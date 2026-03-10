"""
Finhaus — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.routers import feed, company, earnings, watchlist, search
from app.routers import market, portfolio
from app.services import market_data, alpaca_service

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Startup
    await init_db()
    yield
    # Shutdown
    await market_data.close_client()
    await alpaca_service.close_client()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Finhaus — Bloomberg-style Financial Terminal API",
    lifespan=lifespan,
)

# CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # Next.js dev server
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(market.router, prefix="/api/v1/market", tags=["market"])
app.include_router(feed.router, prefix="/api/v1/feed", tags=["feed"])
app.include_router(company.router, prefix="/api/v1/company", tags=["company"])
app.include_router(earnings.router, prefix="/api/v1/earnings", tags=["earnings"])
app.include_router(watchlist.router, prefix="/api/v1/watchlist", tags=["watchlist"])
app.include_router(search.router, prefix="/api/v1/search", tags=["search"])
app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["portfolio"])


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "alpaca_connected": alpaca_service.is_configured(),
    }
