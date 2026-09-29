"""
League router - league/competition endpoints.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import logger
from app.schemas.league import LeagueResponse, LeagueListResponse, LeagueCreate
from app.services.league_service import LeagueService

router = APIRouter(prefix="/leagues", tags=["Leagues"])


@router.get("", response_model=LeagueListResponse)
async def list_leagues(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=200, description="Items per page"),
    callback: Optional[str] = Query(None, description="JSONP callback function name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of all football leagues/competitions.

    - **page**: Page number (1-based)
    - **page_size**: Items per page (max 200)
    """
    skip = (page - 1) * page_size
    items, total = await LeagueService.get_leagues(db, skip=skip, limit=page_size)
    response = LeagueListResponse(total=total, items=items)

    if callback:
        return Response(
            content=f"{callback}({response.model_dump_json()});",
            media_type="application/javascript"
        )

    return response


@router.get("/{league_id}", response_model=LeagueResponse)
async def get_league(
    league_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get information about a specific league.

    - **league_id**: League internal ID
    """
    league = await LeagueService.get_league_by_id(db, league_id)
    if not league:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"League with ID {league_id} not found"
        )
    return league


@router.post("", response_model=LeagueResponse, status_code=status.HTTP_201_CREATED)
async def create_league(
    league_data: LeagueCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new league (for admin use).
    """
    try:
        league = await LeagueService.create_league(db, league_data)
        return league
    except Exception as e:
        logger.error(f"Failed to create league: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create league: {str(e)}"
        )
