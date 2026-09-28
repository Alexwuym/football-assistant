"""Crawler router - manual trigger endpoints for Sporttery data collection."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.sporttery_crawler import SportteryCrawlerService

router = APIRouter(prefix="/crawler", tags=["Crawler"])


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_crawler(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger Sporttery data crawl.

    Fetches latest match schedules and odds from sporttery.cn
    and updates the database. This endpoint is idempotent - running
    it multiple times will update existing records rather than create duplicates.
    """
    try:
        logger.info("Manual crawler trigger received")
        crawler = SportteryCrawlerService(db)
        result = await crawler.crawl()
        return {
            "success": True,
            "message": "Crawl completed successfully",
            "data": result,
        }
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawler failed: {str(e)}"
        )


@router.get("/status")
async def crawler_status():
    """Get crawler status and configuration."""
    return {
        "status": "ready",
        "source": "sporttery.cn",
        "api_url": "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry",
        "note": "Use POST /api/crawler/run to trigger manual crawl",
    }


@router.get("/debug-fetch")
async def debug_fetch():
    """Debug endpoint: directly fetch sporttery API and return diagnostics."""
    import httpx
    import time
    
    url = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"
    params = {
        "poolCode": ["had", "hhad"],
        "_": str(int(time.time() * 1000))
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.sporttery.cn/",
    }
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=headers)
            body = resp.text[:2000]
            try:
                json_body = resp.json()
                json_preview = {k: v for k, v in json_body.items() if k != "value"}
                if "value" in json_body and isinstance(json_body["value"], dict):
                    mil = json_body["value"].get("matchInfoList", [])
                    json_preview["matchInfoList_count"] = len(mil)
            except Exception:
                json_preview = None
                
            return {
                "status_code": resp.status_code,
                "headers": dict(resp.headers),
                "body_preview": body,
                "json_preview": json_preview,
            }
    except Exception as e:
        return {
            "error": str(e),
            "error_type": type(e).__name__,
        }
