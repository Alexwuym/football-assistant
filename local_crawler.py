"""Local crawler script for fetching Sporttery data and pushing to Render backend.

This script is designed to run in GitHub Actions. It fetches match data
from sporttery.cn and POSTs the raw JSON payload to the Render backend's
/api/crawler/ingest endpoint.
"""
import json
import logging
import os
import sys
import time
from typing import Dict, Optional

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Pool codes for different bet types
POOL_CODES = ["had", "hhad", "crs", "ttg", "hafu"]

# Sporttery API endpoint
SPORTTERY_API_URL = (
    "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"
)

# Render backend ingest endpoint
RENDER_INGEST_URL = (
    "https://football-assistant-api.onrender.com/api/crawler/ingest"
)


def build_api_url(pool_codes: Optional[list] = None) -> str:
    """Build Sporttery API URL with pool codes."""
    codes = pool_codes or POOL_CODES
    params = "&".join([f"poolCode={c}" for c in codes])
    timestamp = int(time.time() * 1000)
    return f"{SPORTTERY_API_URL}?{params}&_={timestamp}"


def get_headers() -> Dict[str, str]:
    """Get HTTP request headers with mobile user-agent."""
    return {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.sporttery.cn/",
        "Connection": "keep-alive",
    }


def fetch_sporttery_data(max_retries: int = 3, retry_delay: int = 5) -> Optional[Dict]:
    """Fetch data from Sporttery API with retry logic."""
    url = build_api_url()
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching Sporttery data (attempt {attempt}/{max_retries})...")
            logger.info(f"URL: {url[:120]}...")
            resp = requests.get(url, headers=get_headers(), timeout=30)
            logger.info(f"Response status: {resp.status_code}")

            if resp.status_code != 200:
                last_error = f"HTTP {resp.status_code}: {resp.text[:500]}"
                logger.warning(last_error)
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue

            try:
                data = resp.json()
            except Exception as e:
                last_error = f"JSON parse error: {e}, text: {resp.text[:500]}"
                logger.warning(last_error)
                if attempt < max_retries:
                    time.sleep(retry_delay)
                continue

            error_code = data.get("errorCode")
            success = data.get("success")
            is_ok = (error_code == 0 or error_code == "0") and success is True
            if is_ok:
                match_info_list = data.get("value", {}).get("matchInfoList", [])
                total_matches = sum(
                    len(day.get("subMatchList", []))
                    for day in match_info_list
                )
                logger.info(f"Sporttery data fetched successfully: {total_matches} matches")
                return data
            else:
                error_msg = data.get("errorMessage", "Unknown API error")
                last_error = f"API error: {error_msg} (code={error_code}, success={success})"
                logger.warning(last_error)
                if attempt < max_retries:
                    time.sleep(retry_delay)
        except requests.Timeout:
            last_error = f"Request timeout (attempt {attempt})"
            logger.warning(last_error)
            if attempt < max_retries:
                time.sleep(retry_delay)
        except requests.RequestException as e:
            last_error = f"Request error: {e} (attempt {attempt})"
            logger.warning(last_error)
            if attempt < max_retries:
                time.sleep(retry_delay)

    logger.error(f"Failed to fetch data after {max_retries} attempts. Last error: {last_error}")
    return None


def push_to_render(data: Dict) -> bool:
    """Push fetched data to Render backend ingest endpoint."""
    api_key = os.environ.get("RENDER_API_KEY")
    if not api_key:
        logger.error("RENDER_API_KEY environment variable is not set")
        return False

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }

    payload = {"data": data}

    try:
        logger.info(f"Pushing data to Render backend: {RENDER_INGEST_URL}")
        resp = requests.post(
            RENDER_INGEST_URL,
            headers=headers,
            json=payload,
            timeout=60,
        )
        logger.info(f"Render response status: {resp.status_code}")

        if resp.status_code == 200:
            result = resp.json()
            logger.info(f"Ingest result: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return True
        else:
            logger.error(f"Render ingest failed: HTTP {resp.status_code} - {resp.text[:500]}")
            return False
    except requests.Timeout:
        logger.error("Render ingest request timed out")
        return False
    except requests.RequestException as e:
        logger.error(f"Render ingest request failed: {e}")
        return False


def main() -> int:
    """Main entry point."""
    logger.info("=== Sporttery Local Crawler Started ===")

    # Step 1: Fetch data from Sporttery
    data = fetch_sporttery_data()
    if not data:
        logger.error("Failed to fetch data from Sporttery API")
        return 1

    # Step 2: Push data to Render backend
    success = push_to_render(data)
    if not success:
        logger.error("Failed to push data to Render backend")
        return 1

    logger.info("=== Sporttery Local Crawler Completed Successfully ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
