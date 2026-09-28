#!/usr/bin/env python3
"""
500彩票网数据抓取器 - 竞彩足球购买助手
================================================
数据源: 500.com (替代已封禁的 sporttery.cn)
接口:
  - https://ews.500.com/static/ews/jczq/jczq.json  (竞彩足球)
  - https://ews.500.com/static/ews/bjdc/bjdc.json  (北京单场)
推送方式:
  1. 首选: 直接调用 Render API (/api/fixtures, /api/odds batch)
  2. 备选: 直接连接 PostgreSQL (需 DATABASE_URL 环境变量)

已知问题 (2026-09-28):
  - Render 后端 POST /api/fixtures 存在 SQLAlchemy async bug，
    返回 500 Internal Server Error（与请求数据无关）。
  - /api/crawler/ingest 仅支持 sporttery 原始格式，不支持 500彩票网格式。
  - 建议修复后端后，本脚本可直接使用。
"""

import os
import sys
import json
import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any

# 尝试导入 asyncpg 用于直接数据库操作
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

import requests

# =============================================================================
# 配置
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

API_BASE_URL = os.environ.get("API_BASE_URL", "https://football-assistant-api.onrender.com")
DATABASE_URL = os.environ.get("DATABASE_URL", "")
JCZQ_URL = "https://ews.500.com/static/ews/jczq/jczq.json"
BJDC_URL = "https://ews.500.com/static/ews/bjdc/bjdc.json"
REQUEST_TIMEOUT = 30
USE_DIRECT_DB = os.environ.get("USE_DIRECT_DB", "false").lower() == "true"

# 500彩票网状态码 → API 状态枚举映射
STATUS_MAP = {
    "0": "SCHEDULED",
    "1": "LIVE",
    "2": "HALFTIME",
    "3": "LIVE",
    "4": "FINISHED",
    "-1": "POSTPONED",
    "-2": "CANCELLED",
    "-3": "SUSPENDED",
    "-4": "SUSPENDED",
}

# 缓存
_league_cache: Dict[str, int] = {}
_team_cache: Dict[str, int] = {}


# =============================================================================
# HTTP 工具
# =============================================================================
def api_get(endpoint: str, params: Optional[Dict] = None) -> Optional[Dict]:
    url = f"{API_BASE_URL}{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"GET {url} failed: {e}")
        return None


def api_post(endpoint: str, payload: Dict) -> Optional[Dict]:
    url = f"{API_BASE_URL}{endpoint}"
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        try:
            err_body = e.response.json()
            logger.error(f"POST {url} HTTP {e.response.status_code}: {err_body}")
        except Exception:
            logger.error(f"POST {url} HTTP {e.response.status_code}: {e.response.text[:300]}")
        return None
    except Exception as e:
        logger.error(f"POST {url} failed: {e}")
        return None


# =============================================================================
# 500彩票网数据抓取
# =============================================================================
def fetch_500_json(url: str) -> Optional[Dict]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0",
            "Accept": "application/json",
            "Referer": "https://www.500.com/",
        }
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") != "100":
            logger.warning(
                f"500 API returned status={data.get('status')}, message={data.get('message')}"
            )
            return None
        return data.get("data", {})
    except Exception as e:
        logger.error(f"Fetch {url} failed: {e}")
        return None


def parse_odds(odds_str: str) -> Tuple[Optional[float], ...]:
    if not odds_str or odds_str.strip() == "":
        return None, None, None
    parts = odds_str.split("/")
    if len(parts) != 3:
        return None, None, None
    try:
        return float(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        return None, None, None


# =============================================================================
# API 模式: 通过 Render REST API 推送数据
# =============================================================================
def get_or_create_league_api(league_name: str) -> Optional[int]:
    cache_key = league_name
    if cache_key in _league_cache:
        return _league_cache[cache_key]

    existing = api_get("/api/leagues", {"page_size": 200})
    if existing and "items" in existing:
        for league in existing["items"]:
            if league.get("name_cn") == league_name:
                _league_cache[cache_key] = league["id"]
                return league["id"]

    payload = {
        "league_id": f"500com_{league_name}",
        "name_cn": league_name,
        "name_en": league_name,
        "country": "中国",
    }
    result = api_post("/api/leagues", payload)
    if result and "id" in result:
        _league_cache[cache_key] = result["id"]
        logger.info(f"Created league: {league_name} (id={result['id']})")
        return result["id"]
    logger.error(f"Failed to create/get league: {league_name}")
    return None


def get_or_create_team_api(team_name: str, league_id: int) -> Optional[int]:
    cache_key = f"{league_id}:{team_name}"
    if cache_key in _team_cache:
        return _team_cache[cache_key]

    existing = api_get("/api/teams", {"page_size": 200})
    if existing and "items" in existing:
        for team in existing["items"]:
            if team.get("name_cn") == team_name:
                _team_cache[cache_key] = team["id"]
                return team["id"]

    payload = {
        "team_id": f"500com_{team_name}",
        "name_cn": team_name,
        "name_en": team_name,
        "short_name": team_name,
        "league_id": league_id,
    }
    result = api_post("/api/teams", payload)
    if result and "id" in result:
        _team_cache[cache_key] = result["id"]
        logger.info(f"Created team: {team_name} (id={result['id']})")
        return result["id"]
    logger.error(f"Failed to create/get team: {team_name}")
    return None


def build_fixture_payload(match: Dict, league_id: int, home_team_id: int, away_team_id: int) -> Dict:
    fid = match.get("fid", "")
    order = match.get("order", "")
    match_time = match.get("matchtime", "")
    status_code = str(match.get("status", "0"))
    home_score = match.get("homescore", "")
    away_score = match.get("awayscore", "")
    home_half_score = match.get("homehalfscore", "")
    away_half_score = match.get("awayhalfscore", "")
    matchround = match.get("matchround", "")

    status = STATUS_MAP.get(status_code, "SCHEDULED")
    home_score_int = int(home_score) if home_score != "" else None
    away_score_int = int(away_score) if away_score != "" else None
    home_half_int = int(home_half_score) if home_half_score != "" else None
    away_half_int = int(away_half_score) if away_half_score != "" else None
    is_jc = 1 if order else 0

    # 北京时间 → UTC (减 8 小时)
    try:
        dt = datetime.strptime(match_time, "%Y-%m-%d %H:%M:%S")
        dt_utc = dt - timedelta(hours=8)
        match_date = dt_utc.strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError:
        match_date = match_time

    return {
        "fixture_id": f"500com_{fid}",
        "match_date": match_date,
        "round_info": matchround if matchround else None,
        "venue": None,
        "referee": None,
        "status": status,
        "status_short": None,
        "elapsed": None,
        "home_score": home_score_int,
        "away_score": away_score_int,
        "home_halftime_score": home_half_int,
        "away_halftime_score": away_half_int,
        "is_jc": is_jc,
        "jc_issue_no": order if order else None,
        "is_hot": 0,
        "source": "500com",
        "league_id": league_id,
        "home_team_id": home_team_id,
        "away_team_id": away_team_id,
    }


def build_odds_payloads(match: Dict, fixture_id: int) -> List[Dict]:
    odds_items = []
    extra_info = match.get("extra_info", {})
    rangqiu = str(match.get("rangqiu", "0"))
    currodds = extra_info.get("currodds", "")
    w, d, l = parse_odds(currodds)

    if w is not None and d is not None and l is not None:
        # 标准盘 SP_WDW
        odds_items.append({
            "odds_type": "SP_WDW", "option_code": "H", "option_name": "主胜",
            "odds_value": w, "handicap": None, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
        odds_items.append({
            "odds_type": "SP_WDW", "option_code": "D", "option_name": "平",
            "odds_value": d, "handicap": None, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
        odds_items.append({
            "odds_type": "SP_WDW", "option_code": "A", "option_name": "客胜",
            "odds_value": l, "handicap": None, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
        # 让球盘 SP_HDP
        odds_items.append({
            "odds_type": "SP_HDP", "option_code": "H", "option_name": "主胜",
            "odds_value": w, "handicap": rangqiu, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
        odds_items.append({
            "odds_type": "SP_HDP", "option_code": "D", "option_name": "平",
            "odds_value": d, "handicap": rangqiu, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
        odds_items.append({
            "odds_type": "SP_HDP", "option_code": "A", "option_name": "客胜",
            "odds_value": l, "handicap": rangqiu, "is_stopped": 0,
            "is_recommended": 0, "confidence": None, "source": "500com",
            "fixture_id": fixture_id,
        })
    return odds_items


def process_matches_api(matches: List[Dict], source_label: str) -> Tuple[int, int, int, int]:
    fixtures_ok = fixtures_fail = odds_ok = odds_fail = 0

    for match in matches:
        league_name = match.get("simpleleague", "").strip()
        home_name = match.get("homesxname", "").strip()
        away_name = match.get("awaysxname", "").strip()
        fid = match.get("fid", "")

        if not league_name or not home_name or not away_name:
            logger.warning(f"Skip match with missing names: fid={fid}")
            fixtures_fail += 1
            continue

        league_id = get_or_create_league_api(league_name)
        if not league_id:
            fixtures_fail += 1
            continue

        home_team_id = get_or_create_team_api(home_name, league_id)
        away_team_id = get_or_create_team_api(away_name, league_id)
        if not home_team_id or not away_team_id:
            fixtures_fail += 1
            continue

        fixture_payload = build_fixture_payload(match, league_id, home_team_id, away_team_id)
        external_id = fixture_payload["fixture_id"]

        # 检查是否已存在
        existing = api_get(f"/api/fixtures/external/{external_id}")
        if existing and "id" in existing:
            logger.info(f"Fixture exists: {external_id}, skipping creation")
            fixtures_ok += 1
            # 仍然尝试更新赔率（记录赔率变化）
            fixture_id = existing["id"]
            odds_payloads = build_odds_payloads(match, fixture_id)
            if odds_payloads:
                result = api_post("/api/odds/batch", {"items": odds_payloads})
                if result:
                    odds_ok += len(odds_payloads)
                else:
                    odds_fail += len(odds_payloads)
            continue

        result = api_post("/api/fixtures", fixture_payload)
        if result and "id" in result:
            fixture_id = result["id"]
            fixtures_ok += 1
            logger.info(f"Created fixture: {external_id} ({home_name} vs {away_name}), id={fixture_id}")

            odds_payloads = build_odds_payloads(match, fixture_id)
            if odds_payloads:
                odds_result = api_post("/api/odds/batch", {"items": odds_payloads})
                if odds_result:
                    odds_ok += len(odds_payloads)
                    logger.info(f"  Created {len(odds_payloads)} odds for fixture {fixture_id}")
                else:
                    odds_fail += len(odds_payloads)
                    logger.warning(f"  Failed to create odds for fixture {fixture_id}")
        else:
            fixtures_fail += 1
            logger.warning(f"Failed to create fixture: {external_id}")

    return fixtures_ok, fixtures_fail, odds_ok, odds_fail


# =============================================================================
# 直接数据库模式: 通过 asyncpg 直接操作 PostgreSQL
# 需要 DATABASE_URL 环境变量，例如:
#   postgresql://user:pass@host:5432/dbname
# =============================================================================
async def get_or_create_league_db(pool, league_name: str) -> Optional[int]:
    cache_key = league_name
    if cache_key in _league_cache:
        return _league_cache[cache_key]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM leagues WHERE name_cn = $1", league_name
        )
        if row:
            _league_cache[cache_key] = row["id"]
            return row["id"]

        new_id = await conn.fetchval(
            """
            INSERT INTO leagues (league_id, name_cn, name_en, country, logo_url, season, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NULL, NULL, NOW(), NOW())
            ON CONFLICT (league_id) DO UPDATE SET name_cn = EXCLUDED.name_cn, updated_at = NOW()
            RETURNING id
            """,
            f"500com_{league_name}", league_name, league_name, "中国"
        )
        if new_id:
            _league_cache[cache_key] = new_id
            logger.info(f"DB created league: {league_name} (id={new_id})")
        return new_id


async def get_or_create_team_db(pool, team_name: str, league_id: int) -> Optional[int]:
    cache_key = f"{league_id}:{team_name}"
    if cache_key in _team_cache:
        return _team_cache[cache_key]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM teams WHERE name_cn = $1", team_name
        )
        if row:
            _team_cache[cache_key] = row["id"]
            return row["id"]

        new_id = await conn.fetchval(
            """
            INSERT INTO teams (team_id, name_cn, name_en, short_name, logo_url, founded, stadium, league_id, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NULL, NULL, NULL, $5, NOW(), NOW())
            ON CONFLICT (team_id) DO UPDATE SET name_cn = EXCLUDED.name_cn, updated_at = NOW()
            RETURNING id
            """,
            f"500com_{team_name}", team_name, team_name, team_name, league_id
        )
        if new_id:
            _team_cache[cache_key] = new_id
            logger.info(f"DB created team: {team_name} (id={new_id})")
        return new_id


async def upsert_fixture_db(pool, match: Dict, league_id: int, home_team_id: int, away_team_id: int) -> Optional[int]:
    fixture_payload = build_fixture_payload(match, league_id, home_team_id, away_team_id)
    external_id = fixture_payload["fixture_id"]

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id FROM fixtures WHERE fixture_id = $1", external_id
        )
        if row:
            fixture_id = row["id"]
            # 更新现有记录
            await conn.execute(
                """
                UPDATE fixtures SET
                    match_date = $1,
                    status = $2,
                    home_score = $3,
                    away_score = $4,
                    home_halftime_score = $5,
                    away_halftime_score = $6,
                    is_jc = $7,
                    jc_issue_no = $8,
                    updated_at = NOW()
                WHERE id = $9
                """,
                fixture_payload["match_date"],
                fixture_payload["status"],
                fixture_payload["home_score"],
                fixture_payload["away_score"],
                fixture_payload["home_halftime_score"],
                fixture_payload["away_halftime_score"],
                fixture_payload["is_jc"],
                fixture_payload["jc_issue_no"],
                fixture_id,
            )
            logger.info(f"DB updated fixture: {external_id} (id={fixture_id})")
            return fixture_id
        else:
            new_id = await conn.fetchval(
                """
                INSERT INTO fixtures (
                    fixture_id, match_date, round_info, venue, referee, status, status_short,
                    elapsed, home_score, away_score, home_halftime_score, away_halftime_score,
                    is_jc, jc_issue_no, is_hot, source, league_id, home_team_id, away_team_id,
                    created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,NOW(),NOW())
                RETURNING id
                """,
                fixture_payload["fixture_id"],
                fixture_payload["match_date"],
                fixture_payload["round_info"],
                fixture_payload["venue"],
                fixture_payload["referee"],
                fixture_payload["status"],
                fixture_payload["status_short"],
                fixture_payload["elapsed"],
                fixture_payload["home_score"],
                fixture_payload["away_score"],
                fixture_payload["home_halftime_score"],
                fixture_payload["away_halftime_score"],
                fixture_payload["is_jc"],
                fixture_payload["jc_issue_no"],
                fixture_payload["is_hot"],
                fixture_payload["source"],
                fixture_payload["league_id"],
                fixture_payload["home_team_id"],
                fixture_payload["away_team_id"],
            )
            logger.info(f"DB created fixture: {external_id} (id={new_id})")
            return new_id


async def insert_odds_db(pool, match: Dict, fixture_id: int):
    odds_payloads = build_odds_payloads(match, fixture_id)
    async with pool.acquire() as conn:
        for odd in odds_payloads:
            await conn.execute(
                """
                INSERT INTO odds (
                    odds_type, option_code, option_name, odds_value, handicap,
                    is_stopped, is_recommended, confidence, source, fixture_id, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,NOW())
                """,
                odd["odds_type"], odd["option_code"], odd["option_name"],
                odd["odds_value"], odd["handicap"],
                odd["is_stopped"], odd["is_recommended"],
                odd["confidence"], odd["source"], odd["fixture_id"],
            )
    return len(odds_payloads)


async def process_matches_db(pool, matches: List[Dict]) -> Tuple[int, int, int, int]:
    fixtures_ok = fixtures_fail = odds_ok = odds_fail = 0
    for match in matches:
        league_name = match.get("simpleleague", "").strip()
        home_name = match.get("homesxname", "").strip()
        away_name = match.get("awaysxname", "").strip()
        if not league_name or not home_name or not away_name:
            fixtures_fail += 1
            continue

        league_id = await get_or_create_league_db(pool, league_name)
        if not league_id:
            fixtures_fail += 1
            continue

        home_team_id = await get_or_create_team_db(pool, home_name, league_id)
        away_team_id = await get_or_create_team_db(pool, away_name, league_id)
        if not home_team_id or not away_team_id:
            fixtures_fail += 1
            continue

        fixture_id = await upsert_fixture_db(pool, match, league_id, home_team_id, away_team_id)
        if fixture_id:
            fixtures_ok += 1
            n = await insert_odds_db(pool, match, fixture_id)
            odds_ok += n
        else:
            fixtures_fail += 1
    return fixtures_ok, fixtures_fail, odds_ok, odds_fail


# =============================================================================
# 主流程
# =============================================================================
async def main_async():
    logger.info("=" * 70)
    logger.info("500彩票网数据抓取器启动")
    logger.info(f"API 地址: {API_BASE_URL}")
    logger.info(f"数据库直连模式: {USE_DIRECT_DB} (asyncpg available: {HAS_ASYNCPG})")
    logger.info("=" * 70)

    total_f_ok = total_f_fail = total_o_ok = total_o_fail = 0

    # 抓取竞彩足球
    logger.info("[1/2] 抓取竞彩足球数据...")
    jczq_data = fetch_500_json(JCZQ_URL)
    jczq_matches = jczq_data.get("matches", []) if jczq_data else []
    logger.info(f"获取到 {len(jczq_matches)} 场竞彩足球比赛")

    # 抓取北京单场
    logger.info("[2/2] 抓取北京单场数据...")
    bjdc_data = fetch_500_json(BJDC_URL)
    bjdc_matches = bjdc_data.get("matches", []) if bjdc_data else []
    logger.info(f"获取到 {len(bjdc_matches)} 场北京单场比赛")

    all_matches = jczq_matches + bjdc_matches
    logger.info(f"总计: {len(all_matches)} 场比赛待处理")

    if not all_matches:
        logger.warning("未获取到任何比赛数据，退出")
        sys.exit(1)

    if USE_DIRECT_DB and HAS_ASYNCPG and DATABASE_URL:
        logger.info("使用直接数据库模式...")
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
        try:
            s, f, os, of = await process_matches_db(pool, all_matches)
            total_f_ok += s
            total_f_fail += f
            total_o_ok += os
            total_o_fail += of
        finally:
            await pool.close()
    else:
        logger.info("使用 API 模式...")
        s, f, os, of = process_matches_api(all_matches, "combined")
        total_f_ok += s
        total_f_fail += f
        total_o_ok += os
        total_o_fail += of

    logger.info("=" * 70)
    logger.info("抓取完成，汇总:")
    logger.info(f"  比赛: 成功={total_f_ok}, 失败={total_f_fail}")
    logger.info(f"  赔率: 成功={total_o_ok}, 失败={total_o_fail}")
    logger.info("=" * 70)

    if total_f_fail > 0 or total_o_fail > 0:
        logger.warning("存在失败项")
        sys.exit(1)

    logger.info("全部成功！")
    sys.exit(0)


def main():
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
