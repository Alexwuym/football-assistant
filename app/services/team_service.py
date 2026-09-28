"""
Team service - business logic for teams.
"""
from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.team import Team
from app.schemas.team import TeamCreate


class TeamService:
    """Service for team operations."""

    @staticmethod
    async def get_teams(
        db: AsyncSession,
        league_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[Team], int]:
        """Get paginated list of teams."""
        query = select(Team)
        if league_id:
            query = query.where(Team.league_id == league_id)

        # Get total count
        count_query = select(func.count(Team.id))
        if league_id:
            count_query = count_query.where(Team.league_id == league_id)
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.order_by(Team.name_cn).offset(skip).limit(limit)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def get_team_by_id(db: AsyncSession, team_id: int) -> Optional[Team]:
        """Get team by internal ID."""
        result = await db.execute(select(Team).where(Team.id == team_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_team_by_external_id(db: AsyncSession, external_id: str) -> Optional[Team]:
        """Get team by external ID."""
        result = await db.execute(select(Team).where(Team.team_id == external_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create_team(db: AsyncSession, team_data: TeamCreate) -> Team:
        """Create a new team."""
        # Check if team already exists
        existing = await TeamService.get_team_by_external_id(db, team_data.team_id)
        if existing:
            return existing

        db_team = Team(**team_data.model_dump())
        db.add(db_team)
        await db.flush()
        await db.refresh(db_team)
        return db_team

    @staticmethod
    async def create_teams_batch(db: AsyncSession, teams_data: List[TeamCreate]) -> List[Team]:
        """Batch create teams."""
        created = []
        for data in teams_data:
            team = await TeamService.create_team(db, data)
            created.append(team)
        return created
