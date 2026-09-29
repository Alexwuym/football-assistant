"""
Football Betting Assistant - FastAPI Application Entry Point.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import traceback

from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.logging import logger
from app.routers import health, fixtures, leagues, teams, odds, crawler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - handles startup and shutdown."""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        # Don't fail startup - CloudBase may need retry
    yield
    # Shutdown
    logger.info("Shutting down application")
    await close_db()


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Backend API for Football Betting Assistant - provides match schedules, odds, and betting recommendations.",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
# Note: allow_credentials must be False when allow_origins=["*"], otherwise
# browsers reject the wildcard Access-Control-Allow-Origin header.
# This API is public (no auth cookies needed), so credentials=False is safe.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests."""
    start_time = time.time()
    path = request.url.path

    # Skip health check logging to reduce noise
    if not path.startswith("/health"):
        logger.info(f"{request.method} {path} - Started")

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        if not path.startswith("/health"):
            logger.info(f"{request.method} {path} - {response.status_code} - {duration:.3f}s")

        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"{request.method} {path} - ERROR - {duration:.3f}s - {str(e)}")
        raise


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An unexpected error occurred"
        }
    )


# Include routers
# Health check at root path (no /api prefix) for monitoring tools
app.include_router(health.router)
# API routes under /api prefix
app.include_router(fixtures.router, prefix=settings.API_PREFIX)
app.include_router(leagues.router, prefix=settings.API_PREFIX)
app.include_router(teams.router, prefix=settings.API_PREFIX)
app.include_router(odds.router, prefix=settings.API_PREFIX)
app.include_router(crawler.router, prefix=settings.API_PREFIX)


@app.get("/")
async def root():
    """Root endpoint - API info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }
