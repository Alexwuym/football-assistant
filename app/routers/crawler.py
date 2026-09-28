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
    return {
        "status": "ready",
        "source": "sporttery.cn",
        "api_url": "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry",
        "note": "Use POST /api/crawler/run to trigger manual crawl",
    }


@router.get("/debug-fetch")
async def debug_fetch():
    """Debug endpoint: test multiple fetch strategies."""
    import httpx
    import time
    
    results = {}
    
    # Strategy 1: Direct request (current approach)
    url = "https://webapi.sporttery.cn/gateway/jc/football/getMatchCalculatorV1.qry"
    params = {
        "poolCode": ["had", "hhad"],
        "_": str(int(time.time() * 1000))
    }
    base_headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; SM-G960U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": "https://www.sporttery.cn/",
    }
    
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url, params=params, headers=base_headers)
            results["direct"] = {
                "status": resp.status_code,
                "content_type": resp.headers.get("content-type"),
                "is_json": resp.headers.get("content-type", "").startswith("application/json"),
            }
    except Exception as e:
        results["direct"] = {"error": str(e)}
    
    # Strategy 2: Cookie-based request
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            # First visit main page to get cookies
            main_resp = client.get("https://www.sporttery.cn/", headers={
                "User-Agent": base_headers["User-Agent"],
            })
            results["main_page_status"] = main_resp.status_code
            results["main_page_cookies"] = dict(client.cookies)
            
            # Then make API request with cookies
            resp2 = client.get(url, params=params, headers=base_headers)
            results["with_cookies"] = {
                "status": resp2.status_code,
                "content_type": resp2.headers.get("content-type"),
                "is_json": resp2.headers.get("content-type", "").startswith("application/json"),
            }
            if resp2.status_code == 200:
                try:
                    data = resp2.json()
                    results["with_cookies"]["success"] = data.get("success")
                    results["with_cookies"]["errorCode"] = data.get("errorCode")
                except:
                    pass
    except Exception as e:
        results["with_cookies"] = {"error": str(e)}
    
    return results
