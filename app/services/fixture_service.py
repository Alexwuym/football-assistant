"""
Fixture service - business logic for fixtures.
"""
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.fixture import Fixture, FixtureStatus
from app.models.team import Team
from app.models.league import League
from app.schemas.fixture import FixtureCreate, FixtureFilter


class FixtureService:
    """Service for fixture operations."""

    @staticmethod
    async def get_fixtures(
        db: AsyncSession,
        filters: Optional[FixtureFilter] = None,
        skip: int = 0,
        limit: int = 20
    ) -> tuple[List[Fixture], int]:
        """Get paginated list of fixtures with filters."""
        query = select(Fixture).options(
            selectinload(Fixture.league),
            selectinload(Fixture.home_team),
            selectinload(Fixture.away_team),
            selectinload(Fixture.odds)
        )

        # Apply filters
        conditions = []
        if filters:
            if filters.date_from:
                conditions.append(Fixture.match_date >= filters.date_from)
            if filters.date_to:
                conditions.append(Fixture.match_date <= filters.date_to)
            if filters.league_id:
                conditions.append(Fixture.league_id == filters.league_id)
            if filters.status:
                conditions.append(Fixture.status == FixtureStatus(filters.status))
            if filters.is_jc is not None:
                conditions.append(Fixture.is_jc == filters.is_jc)
            if filters.is_hot is not None:
                conditions.append(Fixture.is_hot == filters.is_hot)

        if conditions:
            query = query.where(and_(*conditions))

        # Order by match date
        query = query.order_by(Fixture.match_date)

        # Get total count
        count_query = select(func.count(Fixture.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_fixture_by_id(db: AsyncSession, fixture_id: int) -> Optional[Fixture]:
        """Get fixture by internal ID with all related data."""
        result = await db.execute(
            select(Fixture)
            .options(
                selectinload(Fixture.league),
                selectinload(Fixture.home_team),
                selectinload(Fixture.away_team),
                selectinload(Fixture.odds)
            )
            .where(Fixture.id == fixture_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_fixture_by_external_id(db: AsyncSession, external_id: str) -> Optional[Fixture]:
        """Get fixture by external ID."""
        result = await db.execute(
            select(Fixture)
            .options(
                selectinload(Fixture.league),
                selectinload(Fixture.home_team),
                selectinload(Fixture.away_team),
                selectinload(Fixture.odds)
            )
            .where(Fixture.fixture_id == external_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_fixture(db: AsyncSession, fixture_data: FixtureCreate) -> Fixture:
        """Create a new fixture."""
        # Check if fixture already exists
        existing = await FixtureService.get_fixture_by_external_id(db, fixture_data.fixture_id)
        if existing:
            return existing

        db_fixture = Fixture(**fixture_data.model_dump())
        db.add(db_fixture)
        await db.flush()
        await db.refresh(db_fixture)
        return db_fixture

    @staticmethod
    async def create_fixtures_batch(
        db: AsyncSession,
        fixtures_data: List[FixtureCreate]
    ) -> List[Fixture]:
        """Batch create fixtures."""
        created = []
        for data in fixtures_data:
            fixture = await FixtureService.create_fixture(db, data)
            created.append(fixture)
        return created

    @staticmethod
    async def get_fixtures_by_date(
        db: AsyncSession,
        date: datetime,
        is_jc: Optional[int] = None
    ) -> List[Fixture]:
        """Get fixtures for a specific date."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        query = select(Fixture).options(
            selectinload(Fixture.league),
            selectinload(Fixture.home_team),
            selectinload(Fixture.away_team),
            selectinload(Fixture.odds)
        ).where(
            and_(
                Fixture.match_date >= start_of_day,
                Fixture.match_date < end_of_day
            )
        )

        if is_jc is not None:
            query = query.where(Fixture.is_jc == is_jc)

        query = query.order_by(Fixture.match_date)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_fixture_status(
        db: AsyncSession,
        fixture_id: int,
        status: FixtureStatus,
        home_score: Optional[int] = None,
        away_score: Optional[int] = None
    ) -> Optional[Fixture]:
        """Update fixture status and scores."""
        fixture = await FixtureService.get_fixture_by_id(db, fixture_id)
        if not fixture:
            return None

        fixture.status = status
        if home_score is not None:
            fixture.home_score = home_score
        if away_score is not None:
            fixture.away_score = away_score

        await db.flush()
        await db.refresh(fixture)
        return fixture
