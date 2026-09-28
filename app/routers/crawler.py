"""Crawler router - manual trigger endpoints for Sporttery data collection."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.services.sporttery_crawler import SportteryCrawlerService

router = APIRouter(prefix="/crawler", tags=["Crawler"])


@router.post("/run", status_code=status.HTTP_200_OK)
async def run_crawler(db: AsyncSession = Depends(get_db)):
    try:
        logger.info("Manual crawler trigger received")
        crawler = SportteryCrawlerService(db)
        result = await crawler.crawl()
        return {"success": True, "message": "Crawl completed successfully", "data": result}
    except Exception as e:
        logger.error(f"Crawler failed: {e}")
        raise HTTPException(status_code=500, detail=f"Crawler failed: {str(e)}")


@router.get("/status")
async def crawler_status():
    return {"status": "ready", "source": "sporttery.cn"}


@router.get("/debug-proxies")
async def debug_proxies():
    """Test if any free proxy can reach sporttery."""
    import httpx
    
    results = {}
    target_url = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry?poolCode=had&_=1"
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    }
    
    # Test 1: corsproxy.io
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"https://corsproxy.io/?{target_url}", headers=headers)
            ct = r.headers.get("content-type", "")
            results["corsproxy"] = {
                "status": r.status_code,
                "content_type": ct,
                "is_json": ct.startswith("application/json"),
            }
            if ct.startswith("application/json"):
                results["corsproxy"]["preview"] = r.text[:200]
    except Exception as e:
        results["corsproxy"] = {"error": str(e)[:200]}
    
    # Test 2: allorigins.win
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"https://api.allorigins.win/get?url={target_url}", headers=headers)
            results["allorigins"] = {
                "status": r.status_code,
                "content_type": r.headers.get("content-type"),
            }
    except Exception as e:
        results["allorigins"] = {"error": str(e)[:200]}
    
    return results
