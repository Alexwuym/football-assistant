"""Sporttery.cn data crawler service.

Fetches match schedules and odds from the official Sporttery API
and saves them to the database using the existing async SQLAlchemy models.
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.fixture import Fixture, FixtureStatus
from app.models.league import League
from app.models.odds import Odds, OddsType
from app.models.team import Team
from app.schemas.fixture import FixtureCreate
from app.schemas.odds import OddsCreate


# Pool codes for different bet types
POOL_CODES = ["had", "hhad", "crs", "ttg", "hafu"]

# Status mapping from Sporttery to our model
STATUS_MAP = {
    "Selling": FixtureStatus.SCHEDULED,
    "End": FixtureStatus.FINISHED,
    "Ended": FixtureStatus.FINISHED,
    "Postponed": FixtureStatus.POSTPONED,
    "Cancelled": FixtureStatus.CANCELLED,
}

# Odds type mapping
ODDS_TYPE_MAP = {
    "had": OddsType.SP_WDW,
    "hhad": OddsType.SP_HDP,
    "crs": OddsType.SP_SCORE,
    "ttg": OddsType.SP_TOTAL,
    "hafu": OddsType.SP_HALF,
}

# Option mapping for HAD/HHAD
HAD_OPTIONS = {
    "h": ("H", "主胜"),
    "d": ("D", "平"),
    "a": ("A", "客胜"),
}


def _build_api_url(pool_codes: Optional[List[str]] = None) -> str:
    """Build Sporttery API URL with pool codes."""
    url = getattr(settings, "SPORTTERY_API_URL", "")
    if not url:
        url = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"
    codes = pool_codes or POOL_CODES
    params = "&".join([f"poolCode={c}" for c in codes])
    timestamp = int(time.time() * 1000)
    return f"{url}?{params}&_={timestamp}"


def _get_headers() -> Dict[str, str]:
    """Get HTTP request headers with mobile user-agent."""
    return {
        "User-Agent": getattr(
            settings, "CRAWLER_USER_AGENT",
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://m.sporttery.cn/",
        "Connection": "keep-alive",
    }


def _fetch_data(max_retries: int = 3, retry_delay: int = 5) -> Optional[Dict]:
    """Fetch data from Sporttery API with retry logic."""
    url = _build_api_url()
    last_error = ""

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching Sporttery data (attempt {attempt}/{max_retries})...")
            logger.info(f"URL: {url[:120]}...")
            resp = httpx.get(url, headers=_get_headers(), timeout=30, follow_redirects=True)
            logger.info(f"Response status: {resp.status_code}")
            logger.info(f"Response headers: {dict(resp.headers)}")
            
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
            # Handle both integer 0 and string "0"
            is_ok = (error_code == 0 or error_code == "0") and success is True
            if is_ok:
                logger.info("Sporttery data fetched successfully")
                return data
            else:
                error_msg = data.get("errorMessage", "Unknown API error")
                last_error = f"API error: {error_msg} (code={error_code}, success={success})"
                logger.warning(last_error)
                if attempt < max_retries:
                    time.sleep(retry_delay)
        except httpx.TimeoutException:
            last_error = f"Request timeout (attempt {attempt})"
            logger.warning(last_error)
            if attempt < max_retries:
                time.sleep(retry_delay)
        except httpx.HTTPStatusError as e:
            last_error = f"HTTP error {e.response.status_code} (attempt {attempt})"
            logger.warning(last_error)
            if attempt < max_retries:
                time.sleep(retry_delay)
        except Exception as e:
            last_error = f"Request error: {e} (attempt {attempt})"
            logger.warning(last_error)
            if attempt < max_retries:
                time.sleep(retry_delay)

    logger.error(f"Failed to fetch data after {max_retries} attempts. Last error: {last_error}")
    return None


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


class SportteryCrawlerService:
    """Service for crawling Sporttery.cn data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_or_create_league(self, league_name: str) -> League:
        """Get existing league or create new one."""
        league_id_str = f"sporttery_{league_name}"
        result = await self.db.execute(
            select(League).where(League.league_id == league_id_str)
        )
        league = result.scalar_one_or_none()

        if not league:
            league = League(
                league_id=league_id_str,
                name_cn=league_name,
                name_en=league_name,
                country="中国",
                source="sporttery",
            )
            self.db.add(league)
            await self.db.flush()
            await self.db.refresh(league)
            logger.info(f"Created league: {league_name}")
        return league

    async def _get_or_create_team(self, team_name: str, league_id: int) -> Team:
        """Get existing team or create new one."""
        team_id_str = f"sporttery_{team_name}"
        result = await self.db.execute(
            select(Team).where(Team.team_id == team_id_str)
        )
        team = result.scalar_one_or_none()

        if not team:
            team = Team(
                team_id=team_id_str,
                name_cn=team_name,
                name_en=team_name,
                short_name=team_name,
                league_id=league_id,
                source="sporttery",
            )
            self.db.add(team)
            await self.db.flush()
            await self.db.refresh(team)
            logger.info(f"Created team: {team_name}")
        return team

    async def _get_or_create_fixture(
        self, match_data: Dict, league_id: int,
        home_team_id: int, away_team_id: int
    ) -> Fixture:
        """Get existing fixture or create new one."""
        fixture_id_str = str(match_data.get("matchId", ""))
        result = await self.db.execute(
            select(Fixture).where(Fixture.fixture_id == fixture_id_str)
        )
        fixture = result.scalar_one_or_none()

        match_date_str = match_data.get("matchDate", "")
        match_time_str = match_data.get("matchTime", "00:00:00")
        match_dt = datetime.strptime(
            f"{match_date_str} {match_time_str}", "%Y-%m-%d %H:%M:%S"
        )

        status = STATUS_MAP.get(
            match_data.get("matchStatus", ""),
            FixtureStatus.SCHEDULED
        )
        is_hot = 1 if match_data.get("isHot") else 0

        if fixture:
            # Update existing fixture
            fixture.match_date = match_dt
            fixture.status = status
            fixture.is_hot = is_hot
            fixture.jc_issue_no = match_data.get("matchNumStr", "")
            fixture.is_jc = 1
            fixture.updated_at = datetime.utcnow()
            logger.info(f"Updated fixture: {fixture_id_str}")
        else:
            fixture = Fixture(
                fixture_id=fixture_id_str,
                league_id=league_id,
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                match_date=match_dt,
                status=status,
                is_jc=1,
                jc_issue_no=match_data.get("matchNumStr", ""),
                is_hot=is_hot,
                source="sporttery",
            )
            self.db.add(fixture)
            await self.db.flush()
            await self.db.refresh(fixture)
            logger.info(f"Created fixture: {fixture_id_str}")

        return fixture

    async def _save_odds(self, fixture_id: int, match_data: Dict) -> int:
        """Save odds for a fixture. Returns count of odds saved."""
        count = 0

        # HAD (胜平负)
        had = match_data.get("had", {})
        if had:
            for key, (code, name) in HAD_OPTIONS.items():
                value = _safe_float(had.get(key))
                if value is not None:
                    odds_data = OddsCreate(
                        fixture_id=fixture_id,
                        odds_type=OddsType.SP_WDW,
                        option_code=code,
                        option_name=name,
                        odds_value=value,
                        source="sporttery",
                    )
                    await self._upsert_odds(odds_data)
                    count += 1

        # HHAD (让球胜平负)
        hhad = match_data.get("hhad", {})
        if hhad:
            goal_line = hhad.get("goalLine", "")
            for key, (code, name) in HAD_OPTIONS.items():
                value = _safe_float(hhad.get(key))
                if value is not None:
                    odds_data = OddsCreate(
                        fixture_id=fixture_id,
                        odds_type=OddsType.SP_HDP,
                        option_code=code,
                        option_name=name,
                        odds_value=value,
                        handicap=goal_line,
                        source="sporttery",
                    )
                    await self._upsert_odds(odds_data)
                    count += 1

        # TTG (总进球)
        ttg = match_data.get("ttg", {})
        if ttg:
            for key, value in ttg.items():
                if key.startswith("s") and key != "updateDate" and key != "updateTime":
                    val = _safe_float(value)
                    if val is not None:
                        goals = key[1:]  # e.g., "s0" -> "0"
                        odds_data = OddsCreate(
                            fixture_id=fixture_id,
                            odds_type=OddsType.SP_TOTAL,
                            option_code=key,
                            option_name=f"{goals}球",
                            odds_value=val,
                            source="sporttery",
                        )
                        await self._upsert_odds(odds_data)
                        count += 1

        return count

    async def _upsert_odds(self, odds_data: OddsCreate) -> None:
        """Upsert odds record."""
        result = await self.db.execute(
            select(Odds).where(
                Odds.fixture_id == odds_data.fixture_id,
                Odds.odds_type == odds_data.odds_type,
                Odds.option_code == odds_data.option_code,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.odds_value = odds_data.odds_value
            existing.handicap = odds_data.handicap
            existing.option_name = odds_data.option_name
            existing.updated_at = datetime.utcnow()
        else:
            db_odds = Odds(**odds_data.model_dump())
            self.db.add(db_odds)

    async def crawl(self) -> Dict[str, int]:
        """Run full crawl: fetch data and save to database."""
        start_time = time.time()
        logger.info("Starting Sporttery crawler...")

        data = _fetch_data()
        if not data:
            raise Exception("Failed to fetch data from Sporttery API")

        match_info_list = data.get("value", {}).get("matchInfoList", [])
        fixtures_created = 0
        fixtures_updated = 0
        odds_saved = 0
        total_matches = 0

        for day_info in match_info_list:
            for match in day_info.get("subMatchList", []):
                total_matches += 1
                try:
                    league_name = match.get("leagueAbbName", "未知联赛")
                    home_name = match.get("homeTeamAbbName", "主队")
                    away_name = match.get("awayTeamAbbName", "客队")

                    # Get or create league
                    league = await self._get_or_create_league(league_name)

                    # Get or create teams
                    home_team = await self._get_or_create_team(home_name, league.id)
                    away_team = await self._get_or_create_team(away_name, league.id)

                    # Get or create fixture
                    fixture = await self._get_or_create_fixture(
                        match, league.id, home_team.id, away_team.id
                    )

                    if fixture.created_at == fixture.updated_at:
                        fixtures_created += 1
                    else:
                        fixtures_updated += 1

                    # Save odds
                    odds_count = await self._save_odds(fixture.id, match)
                    odds_saved += odds_count

                    # Throttle - use asyncio.sleep instead of time.sleep
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"Error processing match {match.get('matchId')}: {e}")
                    continue

        await self.db.commit()

        elapsed = time.time() - start_time
        logger.info(
            f"Crawl completed: {total_matches} matches, "
            f"{fixtures_created} created, {fixtures_updated} updated, "
            f"{odds_saved} odds saved, {elapsed:.2f}s"
        )

        return {
            "total_matches": total_matches,
            "fixtures_created": fixtures_created,
            "fixtures_updated": fixtures_updated,
            "odds_saved": odds_saved,
            "elapsed_seconds": round(elapsed, 2),
        }
