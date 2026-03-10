"""
Finhaus — Market data API endpoints.

Serves real-time quotes, indices, charts, and ticker search.
"""

from fastapi import APIRouter, Query
from app.services import market_data

router = APIRouter()


@router.get("/quotes")
async def get_quotes(
    tickers: str = Query(..., description="Comma-separated ticker symbols, e.g. AAPL,MSFT,GOOGL"),
):
    """Get real-time quotes for multiple tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    if not ticker_list:
        return []
    quotes = await market_data.get_batch_quotes(ticker_list)
    return quotes


@router.get("/quote/{ticker}")
async def get_single_quote(ticker: str):
    """Get real-time quote for a single ticker."""
    return await market_data.get_quote(ticker.upper())


@router.get("/indices")
async def get_indices():
    """Get major market indices and commodities (SPX, DJI, IXIC, VIX, BTC, etc.)."""
    return await market_data.get_market_indices()


@router.get("/chart/{ticker}")
async def get_chart(
    ticker: str,
    period: str = Query("1M", description="Chart period: 1D, 1W, 1M, 3M, 1Y, 5Y"),
):
    """Get OHLCV chart data for a ticker."""
    valid_periods = ["1D", "1W", "1M", "3M", "1Y", "5Y"]
    if period.upper() not in valid_periods:
        period = "1M"
    return await market_data.get_stock_chart(ticker.upper(), period.upper())


@router.get("/search")
async def search(
    q: str = Query(..., description="Search query (ticker or company name)"),
    limit: int = Query(10, ge=1, le=25),
):
    """Search for tickers by company name or symbol."""
    return await market_data.search_ticker(q, limit)


@router.get("/profile/{ticker}")
async def get_profile(ticker: str):
    """Get company profile (sector, industry, description, logo)."""
    profile = await market_data.get_company_profile(ticker.upper())
    if not profile:
        return {"error": "Profile not found", "ticker": ticker}
    return profile


@router.get("/news")
async def get_news_feed(
    ticker: str = Query(None, description="Optional ticker to filter news"),
    limit: int = Query(20, ge=1, le=50),
):
    """Get latest financial news, optionally filtered by ticker."""
    return await market_data.get_news(ticker.upper() if ticker else None, limit)


@router.get("/earnings-calendar")
async def get_earnings_calendar(
    from_date: str = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: str = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Get upcoming earnings calendar."""
    return await market_data.get_earnings_calendar(from_date, to_date)
