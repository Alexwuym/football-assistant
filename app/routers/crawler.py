"""Crawler router - manual trigger and external ingest endpoints for Sporttery data."""
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.sporttery_crawler import SportteryCrawlerService

router = APIRouter(prefix="/crawler", tags=["Crawler"])


class IngestPayload(BaseModel):
    data: Dict[str, Any]


@router.post("/run")
async def run_crawler(db: AsyncSession = Depends(get_db)):
    """
    Manually trigger Sporttery data crawl (self-fetched).

    NOTE: This endpoint calls sporttery.cn directly. Render's datacenter
    IPs are blocked by sporttery's WAF (returns 567). Use POST
    /api/crawler/ingest with pre-fetched data instead.
    """
    try:
        crawler = SportteryCrawlerService(db)
        result = await crawler.crawl()
        return {"success": True, "message": "Crawl completed successfully", "data": result}
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise HTTPException(status_code=500, detail=f"Crawler failed: {str(e)}")


@router.post("/ingest")
async def ingest_data(payload: IngestPayload, db: AsyncSession = Depends(get_db)):
    """
    Ingest pre-fetched Sporttery data into the database.

    Use this endpoint to push data fetched from a non-blocked IP
    (e.g., a local script or external scheduler) into the database.
    Send the raw JSON response from the Sporttery API in the `data` field.
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
        "fetch_strategy": "external (sporttery blocks datacenter IPs)",
        "note": "POST /api/crawler/run attempts direct fetch (blocked from Render). POST /api/crawler/ingest accepts pre-fetched data.",
    }