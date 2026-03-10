"""
Finhaus — Watchlist CRUD router.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.models import Watchlist, WatchlistItem, Company
from app.schemas.schemas import WatchlistResponse, WatchlistCreate, WatchlistAddTicker

router = APIRouter()

# Placeholder user_id until auth is implemented
DEFAULT_USER_ID = "default_user"


@router.get("/", response_model=List[WatchlistResponse])
async def get_watchlists(db: AsyncSession = Depends(get_db)):
    """Get all watchlists for the current user."""
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == DEFAULT_USER_ID)
    )
    watchlists = result.scalars().all()

    response = []
    for wl in watchlists:
        # Get tickers in this watchlist
        items_q = await db.execute(
            select(WatchlistItem).where(WatchlistItem.watchlist_id == wl.id)
        )
        items = items_q.scalars().all()

        tickers = []
        for item in items:
            company_q = await db.execute(
                select(Company).where(Company.id == item.company_id)
            )
            company = company_q.scalar_one_or_none()
            if company:
                tickers.append({
                    "ticker": company.ticker,
                    "name": company.name,
                    "sector": company.sector,
                    "industry": company.industry,
                    "market_cap": company.market_cap,
                    "logo_url": company.logo_url,
                })

        response.append({
            "id": wl.id,
            "name": wl.name,
            "tickers": tickers,
            "created_at": wl.created_at,
        })

    return response


@router.post("/", response_model=WatchlistResponse)
async def create_watchlist(
    watchlist: WatchlistCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new watchlist."""
    wl = Watchlist(
        user_id=DEFAULT_USER_ID,
        name=watchlist.name,
    )
    db.add(wl)
    await db.flush()

    # Add initial tickers if provided
    for ticker_symbol in watchlist.tickers:
        company_q = await db.execute(
            select(Company).where(Company.ticker == ticker_symbol.upper())
        )
        company = company_q.scalar_one_or_none()
        if company:
            item = WatchlistItem(
                watchlist_id=wl.id,
                company_id=company.id,
            )
            db.add(item)

    await db.flush()

    return {
        "id": wl.id,
        "name": wl.name,
        "tickers": [],
        "created_at": wl.created_at,
    }


@router.post("/{watchlist_id}/tickers")
async def add_ticker_to_watchlist(
    watchlist_id: int,
    payload: WatchlistAddTicker,
    db: AsyncSession = Depends(get_db),
):
    """Add a ticker to a watchlist."""
    # Verify watchlist exists
    wl_q = await db.execute(
        select(Watchlist).where(Watchlist.id == watchlist_id)
    )
    wl = wl_q.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    # Find or create company
    company_q = await db.execute(
        select(Company).where(Company.ticker == payload.ticker.upper())
    )
    company = company_q.scalar_one_or_none()

    if not company:
        # Create a minimal company record
        company = Company(
            ticker=payload.ticker.upper(),
            name=payload.ticker.upper(),
        )
        db.add(company)
        await db.flush()

    # Add to watchlist (ignore if already exists)
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.company_id == company.id,
        )
    )
    if existing.scalar_one_or_none():
        return {"status": "already_exists", "ticker": payload.ticker}

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        company_id=company.id,
    )
    db.add(item)
    return {"status": "added", "ticker": payload.ticker}


@router.delete("/{watchlist_id}/tickers/{ticker}")
async def remove_ticker_from_watchlist(
    watchlist_id: int,
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """Remove a ticker from a watchlist."""
    company_q = await db.execute(
        select(Company).where(Company.ticker == ticker.upper())
    )
    company = company_q.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Ticker not found")

    await db.execute(
        delete(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.company_id == company.id,
        )
    )
    return {"status": "removed", "ticker": ticker}


@router.delete("/{watchlist_id}")
async def delete_watchlist(
    watchlist_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a watchlist and all its items."""
    wl_q = await db.execute(
        select(Watchlist).where(Watchlist.id == watchlist_id)
    )
    wl = wl_q.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")

    await db.execute(
        delete(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)
    )
    await db.execute(
        delete(Watchlist).where(Watchlist.id == watchlist_id)
    )
    return {"status": "deleted"}
