"""
Finhaus — Earnings router.

Earnings calendar from DB and external APIs.
"""

from fastapi import APIRouter, Depends, Query
from typing import List
from datetime import date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.models import EarningsReport, Company
from app.schemas.schemas import EarningsCalendarItem
from app.services import market_data

router = APIRouter()


@router.get("/calendar", response_model=List[EarningsCalendarItem])
async def get_earnings_calendar(
    start_date: date = None,
    end_date: date = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get earnings calendar from database.
    """
    query = select(EarningsReport).join(Company)

    if start_date:
        query = query.where(EarningsReport.report_date >= start_date)
    if end_date:
        query = query.where(EarningsReport.report_date <= end_date)

    query = query.order_by(EarningsReport.report_date)
    result = await db.execute(query)
    reports = result.scalars().all()

    # If DB is empty, return empty (external API available at /upcoming)
    items = []
    for r in reports:
        company_q = await db.execute(select(Company).where(Company.id == r.company_id))
        company = company_q.scalar_one_or_none()
        items.append(EarningsCalendarItem(
            ticker=company.ticker if company else "",
            company_name=company.name if company else "",
            report_date=r.report_date,
            fiscal_period=r.fiscal_period,
            eps_estimate=r.eps_estimate,
            revenue_estimate=r.revenue_estimate,
        ))

    return items


@router.get("/upcoming")
async def get_upcoming_earnings(
    days: int = Query(14, ge=1, le=90, description="Number of days ahead to look"),
):
    """
    Get upcoming earnings from external API (FMP/Finnhub).
    """
    today = date.today()
    end = today + timedelta(days=days)
    return await market_data.get_earnings_calendar(
        from_date=today.isoformat(),
        to_date=end.isoformat(),
    )
