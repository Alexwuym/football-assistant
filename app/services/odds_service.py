"""
Odds service - business logic for betting odds.
"""
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.odds import Odds, OddsType
from app.schemas.odds import OddsCreate


class OddsService:
    """Service for odds operations."""

    @staticmethod
    async def get_odds_by_fixture(
        db: AsyncSession,
        fixture_id: int,
        odds_type: Optional[OddsType] = None
    ) -> List[Odds]:
        """Get odds for a fixture."""
        query = select(Odds).where(Odds.fixture_id == fixture_id)
        if odds_type:
            query = query.where(Odds.odds_type == odds_type)
        query = query.order_by(Odds.odds_type, Odds.option_code)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_odds_by_id(db: AsyncSession, odds_id: int) -> Optional[Odds]:
        """Get odds by ID."""
        result = await db.execute(select(Odds).where(Odds.id == odds_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_odds(db: AsyncSession, odds_data: OddsCreate) -> Odds:
        """Create or update odds for a fixture."""
        # Check if this odds option already exists
        result = await db.execute(
            select(Odds).where(
                Odds.fixture_id == odds_data.fixture_id,
                Odds.odds_type == odds_data.odds_type,
                Odds.option_code == odds_data.option_code
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing odds
            for key, value in odds_data.model_dump().items():
                if key != "id" and hasattr(existing, key):
                    setattr(existing, key, value)
            await db.flush()
            await db.refresh(existing)
            return existing
        else:
            # Create new odds
            db_odds = Odds(**odds_data.model_dump())
            db.add(db_odds)
            await db.flush()
            await db.refresh(db_odds)
            return db_odds

    @staticmethod
    async def create_odds_batch(db: AsyncSession, odds_data_list: List[OddsCreate]) -> List[Odds]:
        """Batch create or update odds."""
        created = []
        for data in odds_data_list:
            odds = await OddsService.create_odds(db, data)
            created.append(odds)
        return created

    @staticmethod
    async def get_recommended_odds(db: AsyncSession, fixture_id: int) -> List[Odds]:
        """Get AI recommended odds for a fixture."""
        result = await db.execute(
            select(Odds)
            .where(
                Odds.fixture_id == fixture_id,
                Odds.is_recommended == 1
            )
            .order_by(Odds.confidence.desc())
        )
        return list(result.scalars().all())
