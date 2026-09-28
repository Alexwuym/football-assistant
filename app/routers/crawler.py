"""Crawler router - manual trigger endpoints for Sporttery data collection."""
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.sporttery_crawler import SportteryCrawlerService

router = APIRouter(prefix="/crawler", tags=["Crawler"])


class IngestPayload(BaseModel):
    data: Dict[str, Any]


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_crawler(db: AsyncSession = Depends(get_db)):
    """Manually trigger Sporttery data crawl (fetches data itself)."""
    try:
        logger.info("Manual crawler trigger received")
        crawler = SportteryCrawlerService(db)
        result = await crawler.crawl()
        return {"success": True, "message": "Crawl completed successfully", "data": result}
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise HTTPException(status_code=500, detail=f"Crawler failed: {str(e)}")


@router.post("/ingest", status_code=status.HTTP_200_OK)
async def ingest_data(payload: IngestPayload, db: AsyncSession = Depends(get_db)):
    """
    Ingest pre-fetched Sporttery data into the database.

    This endpoint accepts the raw JSON response from the Sporttery API
    (fetched externally to bypass IP-based WAF blocking) and processes
    it the same way the internal crawler would.
    """
    try:
        logger.info("Ingest request received")
        crawler = SportteryCrawlerService(db)
        result = await crawler.process_payload(payload.data)
        return {"success": True, "message": "Ingest completed successfully", "data": result}
    except Exception as e:
        logger.error(f"Ingest failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {str(e)}")


@router.get("/status")
async def crawler_status():
    return {
        "status": "ready",
        "source": "sporttery.cn",
        "api_url": "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry",
        "note": "Use POST /api/crawler/run to trigger manual crawl, or POST /api/crawler/ingest with pre-fetched data",
    }