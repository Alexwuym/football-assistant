"""
Odds router - betting odds endpoints.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import logger
from app.models.odds import OddsType
from app.schemas.odds import OddsResponse, OddsListResponse, OddsCreate, OddsBatchCreate
from app.services.odds_service import OddsService

router = APIRouter(prefix="/odds", tags=["Odds"])


@router.get("/fixture/{fixture_id}", response_model=OddsListResponse)
async def get_fixture_odds(
    fixture_id: int,
    odds_type: Optional[str] = Query(None, description="Filter by odds type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get odds for a specific fixture.

    - **fixture_id**: Fixture internal ID
    - **odds_type**: Filter by odds type (SP_WDW, SP_HDP, SP_SCORE, SP_TOTAL, SP_HALF, SP_BQ)
    """
    type_enum = OddsType(odds_type) if odds_type else None
    items = await OddsService.get_odds_by_fixture(db, fixture_id, odds_type=type_enum)
    return OddsListResponse(total=len(items), items=items)


@router.get("/recommended/{fixture_id}", response_model=OddsListResponse)
async def get_recommended_odds(
    fixture_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get AI recommended odds for a fixture.

    - **fixture_id**: Fixture internal ID
    """
    items = await OddsService.get_recommended_odds(db, fixture_id)
    return OddsListResponse(total=len(items), items=items)


@router.post("", response_model=OddsResponse, status_code=status.HTTP_201_CREATED)
async def create_odds(
    odds_data: OddsCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update odds for a fixture.
    """
    try:
        odds = await OddsService.create_odds(db, odds_data)
        return odds
    except Exception as e:
        logger.error(f"Failed to create odds: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create odds: {str(e)}"
        )


@router.post("/batch", response_model=OddsListResponse, status_code=status.HTTP_201_CREATED)
async def create_odds_batch(
    batch_data: OddsBatchCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch create or update odds.
    """
    try:
        created = await OddsService.create_odds_batch(db, batch_data.items)
        return OddsListResponse(total=len(created), items=created)
    except Exception as e:
        logger.error(f"Failed to batch create odds: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to batch create odds: {str(e)}"
        )
