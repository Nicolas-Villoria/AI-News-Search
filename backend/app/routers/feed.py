"""
Finhaus — Intelligence Feed router.

Serves the ranked market intelligence feed from the database,
and provides a real-time news endpoint via external APIs.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.database import get_db
from app.models.models import IntelligenceItem
from app.schemas.schemas import FeedResponse, IntelligenceItemResponse
from app.services import market_data

router = APIRouter()


@router.get("/", response_model=FeedResponse)
async def get_intelligence_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    source_type: str = Query(None, description="Filter by: earnings_report | sec_filing | analyst_rating | news"),
    ticker: str = Query(None, description="Filter by ticker symbol"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the ranked market intelligence feed.
    Items are ordered by impact_score DESC, then created_at DESC.
    """
    query = select(IntelligenceItem)

    if source_type:
        query = query.where(IntelligenceItem.source_type == source_type)
    if ticker:
        from app.models.models import Company
        subq = select(Company.id).where(Company.ticker == ticker.upper()).scalar_subquery()
        query = query.where(IntelligenceItem.company_id == subq)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate and sort
    query = query.order_by(
        desc(IntelligenceItem.impact_score),
        desc(IntelligenceItem.created_at),
    ).offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/news/{ticker}")
async def get_live_news(
    ticker: str,
    limit: int = Query(20, ge=1, le=50),
):
    """
    Get real-time news for a specific ticker from external APIs.
    This bypasses the database for live, up-to-the-minute news.
    """
    return await market_data.get_news(ticker.upper(), limit)
