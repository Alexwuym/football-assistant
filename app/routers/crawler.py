"""Crawler router - manual trigger endpoints for Sporttery data collection."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.sporttery_crawler import SportteryCrawlerService

router = APIRouter(prefix="/crawler", tags=["Crawler"])


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_crawler(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger Sporttery data crawl.

    Fetches latest match schedules and odds from sporttery.cn
    and updates the database. This endpoint is idempotent - running
    it multiple times will update existing records rather than create duplicates.
    """
    try:
        logger.info("Manual crawler trigger received")
        crawler = SportteryCrawlerService(db)
        result = await crawler.crawl()
        return {
            "success": True,
            "message": "Crawl completed successfully",
            "data": result,
        }
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Crawler failed: {str(e)}"
        )


@router.get("/status")
async def crawler_status():
    """Get crawler status and configuration."""
    return {
        "status": "ready",
        "source": "sporttery.cn",
        "api_url": "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry",
        "note": "Use POST /api/crawler/run to trigger manual crawl",
    }
