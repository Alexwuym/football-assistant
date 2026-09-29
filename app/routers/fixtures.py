"""
Fixture router - match schedule endpoints.
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
import json
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.logging import logger
from app.schemas.fixture import (
    FixtureResponse, FixtureListResponse, FixtureFilter,
    FixtureCreate, FixtureBatchCreate
)
from app.services.fixture_service import FixtureService

router = APIRouter(prefix="/fixtures", tags=["Fixtures"])


@router.get("", response_model=FixtureListResponse)
async def list_fixtures(
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    league_id: Optional[int] = Query(None, description="Filter by league ID"),
    status: Optional[str] = Query(None, description="Filter by match status"),
    is_jc: Optional[int] = Query(None, description="Filter Jingcai matches (0/1)"),
    is_hot: Optional[int] = Query(None, description="Filter hot matches (0/1)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    callback: Optional[str] = Query(None, description="JSONP callback function name"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of fixtures with filtering and pagination.

    - **date_from**: Start date (inclusive)
    - **date_to**: End date (inclusive)
    - **league_id**: Filter by league
    - **status**: Filter by status (SCHEDULED, LIVE, FINISHED, etc.)
    - **is_jc**: Filter Jingcai matches (1 = yes, 0 = no)
    - **is_hot**: Filter hot matches (1 = yes, 0 = no)
    - **page**: Page number (1-based)
    - **page_size**: Items per page (max 100)
    """
    filters = FixtureFilter(
        date_from=date_from,
        date_to=date_to,
        league_id=league_id,
        status=status,
        is_jc=is_jc,
        is_hot=is_hot,
        page=page,
        page_size=page_size
    )

    skip = (page - 1) * page_size
    items, total = await FixtureService.get_fixtures(
        db, filters=filters, skip=skip, limit=page_size
    )

    response = FixtureListResponse(total=total, items=items)

    if callback:
        return Response(
            content=f"{callback}({response.model_dump_json()});",
            media_type="application/javascript"
        )

    return response


@router.get("/{fixture_id}", response_model=FixtureResponse)
async def get_fixture(
    fixture_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific fixture including odds.

    - **fixture_id**: Internal fixture ID
    """
    fixture = await FixtureService.get_fixture_by_id(db, fixture_id)
    if not fixture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture with ID {fixture_id} not found"
        )
    return fixture


@router.get("/external/{external_id}", response_model=FixtureResponse)
async def get_fixture_by_external_id(
    external_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get fixture by external ID.

    - **external_id**: External fixture ID (from data source)
    """
    fixture = await FixtureService.get_fixture_by_external_id(db, external_id)
    if not fixture:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fixture with external ID {external_id} not found"
        )
    return fixture


@router.post("", response_model=FixtureResponse, status_code=status.HTTP_201_CREATED)
async def create_fixture(
    fixture_data: FixtureCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new fixture (for admin/crawler use).
    """
    try:
        fixture = await FixtureService.create_fixture(db, fixture_data)
        return fixture
    except Exception as e:
        logger.error(f"Failed to create fixture: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create fixture: {str(e)}"
        )


@router.post("/batch", response_model=FixtureListResponse, status_code=status.HTTP_201_CREATED)
async def create_fixtures_batch(
    batch_data: FixtureBatchCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch create fixtures (for crawler import).

    - **items**: List of fixture data to create
    """
    try:
        created = await FixtureService.create_fixtures_batch(db, batch_data.items)
        return FixtureListResponse(total=len(created), items=created)
    except Exception as e:
        logger.error(f"Failed to batch create fixtures: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to batch create fixtures: {str(e)}"
        )
