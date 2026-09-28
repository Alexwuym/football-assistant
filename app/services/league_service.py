"""
League service - business logic for leagues.
"""
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.league import League
from app.schemas.league import LeagueCreate, LeagueResponse


class LeagueService:
    """Service for league operations."""

    @staticmethod
    async def get_leagues(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[League], int]:
        """Get paginated list of leagues."""
        # Get total count
        count_result = await db.execute(select(func.count(League.id)))
        total = count_result.scalar()

        # Get items
        result = await db.execute(
            select(League)
            .order_by(League.name_cn)
            .offset(skip)
            .limit(limit)
        )
        items = result.scalars().all()
        return items, total

    @staticmethod
    async def get_league_by_id(db: AsyncSession, league_id: int) -> Optional[League]:
        """Get league by internal ID."""
        result = await db.execute(select(League).where(League.id == league_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_league_by_external_id(db: AsyncSession, external_id: str) -> Optional[League]:
        """Get league by external ID."""
        result = await db.execute(select(League).where(League.league_id == external_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_league(db: AsyncSession, league_data: LeagueCreate) -> League:
        """Create a new league."""
        # Check if league already exists
        existing = await LeagueService.get_league_by_external_id(db, league_data.league_id)
        if existing:
            return existing

        db_league = League(**league_data.model_dump())
        db.add(db_league)
        await db.flush()
        await db.refresh(db_league)
        return db_league

    @staticmethod
    async def create_leagues_batch(db: AsyncSession, leagues_data: List[LeagueCreate]) -> List[League]:
        """Batch create leagues."""
        created = []
        for data in leagues_data:
            league = await LeagueService.create_league(db, data)
            created.append(league)
        return created
