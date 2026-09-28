"""
Team router - team endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import logger
from app.schemas.team import TeamResponse, TeamListResponse, TeamCreate
from app.services.team_service import TeamService

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=TeamListResponse)
async def list_teams(
    league_id: Optional[int] = Query(None, description="Filter by league ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Items per page"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of teams.

    - **league_id**: Filter by league
    - **page**: Page number (1-based)
    - **page_size**: Items per page (max 200)
    """
    skip = (page - 1) * page_size
    items, total = await TeamService.get_teams(
        db, league_id=league_id, skip=skip, limit=page_size
    )
    return TeamListResponse(total=total, items=items)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(
    team_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about a specific team.

    - **team_id**: Team internal ID
    """
    team = await TeamService.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with ID {team_id} not found"
        )
    return team


@router.post("", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    team_data: TeamCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new team (for admin use).
    """
    try:
        team = await TeamService.create_team(db, team_data)
        return team
    except Exception as e:
        logger.error(f"Failed to create team: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create team: {str(e)}"
        )
