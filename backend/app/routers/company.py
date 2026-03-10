"""
Finhaus — Company profile router.

Provides full company data: profile, recent earnings, ratings, news, intelligence.
Falls back to external APIs if not found in database.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.models import Company, EarningsReport, AnalystRating, NewsItem, IntelligenceItem
from app.schemas.schemas import CompanyDeepDive, CompanyResponse
from app.services import market_data

router = APIRouter()


@router.get("/{ticker}")
async def get_company_profile(
    ticker: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get full company profile with recent data.
    First checks DB, then falls back to external APIs.
    """
    ticker = ticker.upper()

    # 1) Try DB first
    result = await db.execute(select(Company).where(Company.ticker == ticker))
    company = result.scalar_one_or_none()

    if company:
        # Fetch related data from DB
        earnings_q = await db.execute(
            select(EarningsReport)
            .where(EarningsReport.company_id == company.id)
            .order_by(desc(EarningsReport.report_date))
            .limit(4)
        )
        ratings_q = await db.execute(
            select(AnalystRating)
            .where(AnalystRating.company_id == company.id)
            .order_by(desc(AnalystRating.action_date))
            .limit(5)
        )
        news_q = await db.execute(
            select(NewsItem)
            .where(NewsItem.company_id == company.id)
            .order_by(desc(NewsItem.published_at))
            .limit(10)
        )
        intel_q = await db.execute(
            select(IntelligenceItem)
            .where(IntelligenceItem.company_id == company.id)
            .order_by(desc(IntelligenceItem.created_at))
            .limit(5)
        )

        return {
            "company": company,
            "recent_earnings": earnings_q.scalars().all(),
            "recent_ratings": ratings_q.scalars().all(),
            "recent_news": news_q.scalars().all(),
            "latest_intelligence": intel_q.scalars().all(),
        }

    # 2) Fallback to external API
    profile = await market_data.get_company_profile(ticker)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")

    quote = await market_data.get_quote(ticker)
    news = await market_data.get_news(ticker, limit=10)

    return {
        "company": {
            "id": 0,
            "ticker": profile["ticker"],
            "name": profile["name"],
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "market_cap": profile.get("market_cap", 0),
            "logo_url": profile.get("logo_url", ""),
            "description": profile.get("description", ""),
            "exchange": profile.get("exchange", ""),
            "website": profile.get("website", ""),
            "ceo": profile.get("ceo", ""),
            "employees": profile.get("employees", ""),
            "country": profile.get("country", ""),
        },
        "quote": quote,
        "recent_earnings": [],
        "recent_ratings": [],
        "recent_news": news,
        "latest_intelligence": [],
    }
