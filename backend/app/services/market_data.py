"""
Finhaus — Market Data Service.

Cascading provider: FMP → Finnhub → Alpha Vantage → yfinance.
In-memory TTL cache for quotes, profiles, charts.
"""

import asyncio
import time
from typing import Optional
import httpx
from app.config import get_settings

settings = get_settings()


# ── In-Memory TTL Cache ─────────────────────────────────────────────────────

class TTLCache:
    """Simple in-memory cache with per-key TTL."""

    def __init__(self):
        self._store: dict[str, tuple[float, any]] = {}

    def get(self, key: str) -> Optional[any]:
        if key in self._store:
            expiry, value = self._store[key]
            if time.time() < expiry:
                return value
            del self._store[key]
        return None

    def set(self, key: str, value: any, ttl: int):
        self._store[key] = (time.time() + ttl, value)

    def clear(self):
        self._store.clear()


_cache = TTLCache()

# TTL constants (seconds)
QUOTE_TTL = 30
PROFILE_TTL = 3600
CHART_TTL = 300
INDEX_TTL = 60
SEARCH_TTL = 600


# ── HTTP Client ─────────────────────────────────────────────────────────────

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(timeout=10.0)
    return _client


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


# ── Quote ────────────────────────────────────────────────────────────────────

async def get_quote(ticker: str) -> dict:
    """Get real-time quote for a single ticker."""
    cache_key = f"quote:{ticker}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_quote_fmp(ticker)
    if not result:
        result = await _fetch_quote_finnhub(ticker)
    if not result:
        result = _get_fallback_quote(ticker)

    _cache.set(cache_key, result, QUOTE_TTL)
    return result


async def get_batch_quotes(tickers: list[str]) -> list[dict]:
    """Get quotes for multiple tickers in parallel."""
    cache_key = f"batch:{','.join(sorted(tickers))}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    # Try FMP batch endpoint first
    result = await _fetch_batch_quotes_fmp(tickers)
    if not result:
        # Fallback to individual requests
        tasks = [get_quote(t) for t in tickers]
        result = await asyncio.gather(*tasks)
        result = [r for r in result if r]

    _cache.set(cache_key, result, QUOTE_TTL)
    return result


async def _fetch_quote_fmp(ticker: str) -> Optional[dict]:
    """Fetch quote from Financial Modeling Prep."""
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            f"https://financialmodelingprep.com/api/v3/quote/{ticker}",
            params={"apikey": settings.FMP_API_KEY},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                q = data[0]
                return {
                    "ticker": q.get("symbol", ticker),
                    "name": q.get("name", ""),
                    "price": q.get("price", 0),
                    "change": q.get("change", 0),
                    "change_pct": q.get("changesPercentage", 0),
                    "volume": q.get("volume", 0),
                    "market_cap": q.get("marketCap", 0),
                    "day_high": q.get("dayHigh", 0),
                    "day_low": q.get("dayLow", 0),
                    "year_high": q.get("yearHigh", 0),
                    "year_low": q.get("yearLow", 0),
                    "open": q.get("open", 0),
                    "prev_close": q.get("previousClose", 0),
                    "pe": q.get("pe"),
                    "eps": q.get("eps"),
                    "exchange": q.get("exchange", ""),
                    "timestamp": q.get("timestamp", 0),
                }
    except Exception:
        pass
    return None


async def _fetch_quote_finnhub(ticker: str) -> Optional[dict]:
    """Fetch quote from Finnhub."""
    if not settings.FINNHUB_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            "https://finnhub.io/api/v1/quote",
            params={"symbol": ticker, "token": settings.FINNHUB_API_KEY},
        )
        if resp.status_code == 200:
            q = resp.json()
            if q and q.get("c", 0) > 0:
                return {
                    "ticker": ticker,
                    "name": "",
                    "price": q.get("c", 0),
                    "change": q.get("d", 0),
                    "change_pct": q.get("dp", 0),
                    "volume": 0,
                    "market_cap": 0,
                    "day_high": q.get("h", 0),
                    "day_low": q.get("l", 0),
                    "year_high": 0,
                    "year_low": 0,
                    "open": q.get("o", 0),
                    "prev_close": q.get("pc", 0),
                    "pe": None,
                    "eps": None,
                    "exchange": "",
                    "timestamp": q.get("t", 0),
                }
    except Exception:
        pass
    return None


def _get_fallback_quote(ticker: str) -> dict:
    """Return empty shell when all providers fail."""
    return {
        "ticker": ticker,
        "name": "",
        "price": 0,
        "change": 0,
        "change_pct": 0,
        "volume": 0,
        "market_cap": 0,
        "day_high": 0,
        "day_low": 0,
        "year_high": 0,
        "year_low": 0,
        "open": 0,
        "prev_close": 0,
        "pe": None,
        "eps": None,
        "exchange": "",
        "timestamp": 0,
    }


async def _fetch_batch_quotes_fmp(tickers: list[str]) -> Optional[list[dict]]:
    """FMP supports batch quotes in a single call."""
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        symbols = ",".join(tickers)
        resp = await client.get(
            f"https://financialmodelingprep.com/api/v3/quote/{symbols}",
            params={"apikey": settings.FMP_API_KEY},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return [
                    {
                        "ticker": q.get("symbol", ""),
                        "name": q.get("name", ""),
                        "price": q.get("price", 0),
                        "change": q.get("change", 0),
                        "change_pct": q.get("changesPercentage", 0),
                        "volume": q.get("volume", 0),
                        "market_cap": q.get("marketCap", 0),
                        "day_high": q.get("dayHigh", 0),
                        "day_low": q.get("dayLow", 0),
                        "year_high": q.get("yearHigh", 0),
                        "year_low": q.get("yearLow", 0),
                        "open": q.get("open", 0),
                        "prev_close": q.get("previousClose", 0),
                        "pe": q.get("pe"),
                        "eps": q.get("eps"),
                        "exchange": q.get("exchange", ""),
                        "timestamp": q.get("timestamp", 0),
                    }
                    for q in data
                ]
    except Exception:
        pass
    return None


# ── Market Indices ───────────────────────────────────────────────────────────

MARKET_INDICES = {
    "SPX": "^GSPC",
    "DJI": "^DJI",
    "IXIC": "^IXIC",
    "RUT": "^RUT",
    "VIX": "^VIX",
    "TNX": "^TNX",
    "DXY": "DX-Y.NYB",
}

COMMODITIES = {
    "CL": "CL=F",    # Crude Oil
    "GC": "GC=F",    # Gold
    "BTC": "BTC-USD", # Bitcoin
}


async def get_market_indices() -> list[dict]:
    """Get major market indices and commodities."""
    cache_key = "indices:all"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_indices_fmp()
    if not result:
        result = _get_fallback_indices()

    _cache.set(cache_key, result, INDEX_TTL)
    return result


async def _fetch_indices_fmp() -> Optional[list[dict]]:
    """Fetch indices from FMP."""
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        # FMP supports index quotes
        symbols = "^GSPC,^DJI,^IXIC,^RUT,^VIX,^TNX"
        resp = await client.get(
            f"https://financialmodelingprep.com/api/v3/quote/{symbols}",
            params={"apikey": settings.FMP_API_KEY},
        )
        results = []
        if resp.status_code == 200:
            data = resp.json()
            label_map = {"^GSPC": "SPX", "^DJI": "DJI", "^IXIC": "IXIC", "^RUT": "RUT", "^VIX": "VIX", "^TNX": "TNX"}
            for q in (data or []):
                sym = q.get("symbol", "")
                results.append({
                    "symbol": label_map.get(sym, sym),
                    "price": q.get("price", 0),
                    "change": q.get("change", 0),
                    "change_pct": q.get("changesPercentage", 0),
                })

        # Also fetch BTC, Gold, Oil
        commodity_symbols = "BTCUSD,GCUSD,CLUSD"
        resp2 = await client.get(
            f"https://financialmodelingprep.com/api/v3/quote/{commodity_symbols}",
            params={"apikey": settings.FMP_API_KEY},
        )
        if resp2.status_code == 200:
            data2 = resp2.json()
            label_map2 = {"BTCUSD": "BTC", "GCUSD": "GC", "CLUSD": "CL"}
            for q in (data2 or []):
                sym = q.get("symbol", "")
                results.append({
                    "symbol": label_map2.get(sym, sym),
                    "price": q.get("price", 0),
                    "change": q.get("change", 0),
                    "change_pct": q.get("changesPercentage", 0),
                })

        if results:
            return results
    except Exception:
        pass
    return None


def _get_fallback_indices() -> list[dict]:
    """Return empty indices when providers fail."""
    indices = ["SPX", "DJI", "IXIC", "RUT", "VIX", "TNX", "DXY", "CL", "GC", "BTC"]
    return [{"symbol": s, "price": 0, "change": 0, "change_pct": 0} for s in indices]


# ── Company Profile ──────────────────────────────────────────────────────────

async def get_company_profile(ticker: str) -> Optional[dict]:
    """Get company profile with sector, industry, description, logo."""
    cache_key = f"profile:{ticker}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_profile_fmp(ticker)
    if not result:
        result = await _fetch_profile_finnhub(ticker)

    if result:
        _cache.set(cache_key, result, PROFILE_TTL)
    return result


async def _fetch_profile_fmp(ticker: str) -> Optional[dict]:
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            f"https://financialmodelingprep.com/api/v3/profile/{ticker}",
            params={"apikey": settings.FMP_API_KEY},
        )
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                p = data[0]
                return {
                    "ticker": p.get("symbol", ticker),
                    "name": p.get("companyName", ""),
                    "sector": p.get("sector", ""),
                    "industry": p.get("industry", ""),
                    "description": p.get("description", ""),
                    "logo_url": p.get("image", ""),
                    "market_cap": p.get("mktCap", 0),
                    "exchange": p.get("exchangeShortName", ""),
                    "website": p.get("website", ""),
                    "ceo": p.get("ceo", ""),
                    "employees": p.get("fullTimeEmployees", ""),
                    "country": p.get("country", ""),
                    "ipo_date": p.get("ipoDate", ""),
                }
    except Exception:
        pass
    return None


async def _fetch_profile_finnhub(ticker: str) -> Optional[dict]:
    if not settings.FINNHUB_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            "https://finnhub.io/api/v1/stock/profile2",
            params={"symbol": ticker, "token": settings.FINNHUB_API_KEY},
        )
        if resp.status_code == 200:
            p = resp.json()
            if p and p.get("name"):
                return {
                    "ticker": p.get("ticker", ticker),
                    "name": p.get("name", ""),
                    "sector": p.get("finnhubIndustry", ""),
                    "industry": p.get("finnhubIndustry", ""),
                    "description": "",
                    "logo_url": p.get("logo", ""),
                    "market_cap": p.get("marketCapitalization", 0) * 1_000_000,
                    "exchange": p.get("exchange", ""),
                    "website": p.get("weburl", ""),
                    "ceo": "",
                    "employees": "",
                    "country": p.get("country", ""),
                    "ipo_date": p.get("ipo", ""),
                }
    except Exception:
        pass
    return None


# ── Stock Chart ──────────────────────────────────────────────────────────────

async def get_stock_chart(ticker: str, period: str = "1M") -> list[dict]:
    """Get OHLCV chart data. period: 1D, 1W, 1M, 3M, 1Y, 5Y."""
    cache_key = f"chart:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_chart_fmp(ticker, period)
    if not result:
        result = []

    _cache.set(cache_key, result, CHART_TTL)
    return result


async def _fetch_chart_fmp(ticker: str, period: str) -> Optional[list[dict]]:
    """Fetch historical price data from FMP."""
    if not settings.FMP_API_KEY:
        return None

    # Map period to FMP endpoint
    period_map = {
        "1D": ("5min", 78),      # 5-min bars for 1 day (~78 bars)
        "1W": ("30min", 70),     # 30-min bars for 1 week
        "1M": ("daily", 22),     # daily bars for 1 month
        "3M": ("daily", 66),     # daily bars for 3 months
        "1Y": ("daily", 252),    # daily bars for 1 year
        "5Y": ("weekly", 260),   # weekly bars for 5 years
    }
    interval, limit = period_map.get(period, ("daily", 22))

    try:
        client = _get_client()

        if interval in ("5min", "30min"):
            url = f"https://financialmodelingprep.com/api/v3/historical-chart/{interval}/{ticker}"
        else:
            url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"

        resp = await client.get(url, params={"apikey": settings.FMP_API_KEY})

        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                bars = data[:limit]
            elif isinstance(data, dict) and "historical" in data:
                bars = data["historical"][:limit]
            else:
                return None

            return [
                {
                    "date": bar.get("date", ""),
                    "open": bar.get("open", 0),
                    "high": bar.get("high", 0),
                    "low": bar.get("low", 0),
                    "close": bar.get("close", 0),
                    "volume": bar.get("volume", 0),
                }
                for bar in reversed(bars)  # Chronological order
            ]
    except Exception:
        pass
    return None


# ── Ticker Search ────────────────────────────────────────────────────────────

async def search_ticker(query: str, limit: int = 10) -> list[dict]:
    """Search for tickers by company name or symbol."""
    if not query or len(query) < 1:
        return []

    cache_key = f"search:{query.lower()}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _search_fmp(query, limit)
    if not result:
        result = await _search_finnhub(query, limit)
    if not result:
        result = []

    _cache.set(cache_key, result, SEARCH_TTL)
    return result


async def _search_fmp(query: str, limit: int) -> Optional[list[dict]]:
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            "https://financialmodelingprep.com/api/v3/search",
            params={
                "query": query,
                "limit": limit,
                "apikey": settings.FMP_API_KEY,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return [
                    {
                        "ticker": item.get("symbol", ""),
                        "name": item.get("name", ""),
                        "exchange": item.get("stockExchange", ""),
                        "type": item.get("type", ""),
                    }
                    for item in data[:limit]
                ]
    except Exception:
        pass
    return None


async def _search_finnhub(query: str, limit: int) -> Optional[list[dict]]:
    if not settings.FINNHUB_API_KEY:
        return None
    try:
        client = _get_client()
        resp = await client.get(
            "https://finnhub.io/api/v1/search",
            params={"q": query, "token": settings.FINNHUB_API_KEY},
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("result", [])
            return [
                {
                    "ticker": item.get("symbol", ""),
                    "name": item.get("description", ""),
                    "exchange": item.get("type", ""),
                    "type": "stock",
                }
                for item in results[:limit]
            ]
    except Exception:
        pass
    return None


# ── News ─────────────────────────────────────────────────────────────────────

async def get_news(ticker: str = None, limit: int = 20) -> list[dict]:
    """Get latest news, optionally filtered by ticker."""
    cache_key = f"news:{ticker or 'general'}:{limit}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_news_fmp(ticker, limit)
    if not result:
        result = await _fetch_news_finnhub(ticker, limit)
    if not result:
        result = []

    _cache.set(cache_key, result, QUOTE_TTL)  # Short TTL for news
    return result


async def _fetch_news_fmp(ticker: str = None, limit: int = 20) -> Optional[list[dict]]:
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        if ticker:
            url = "https://financialmodelingprep.com/api/v3/stock_news"
            params = {"tickers": ticker, "limit": limit, "apikey": settings.FMP_API_KEY}
        else:
            url = "https://financialmodelingprep.com/api/v3/stock_news"
            params = {"limit": limit, "apikey": settings.FMP_API_KEY}

        resp = await client.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return [
                    {
                        "headline": item.get("title", ""),
                        "summary": item.get("text", ""),
                        "source": item.get("site", ""),
                        "url": item.get("url", ""),
                        "image_url": item.get("image", ""),
                        "ticker": item.get("symbol", ""),
                        "published_at": item.get("publishedDate", ""),
                    }
                    for item in data
                ]
    except Exception:
        pass
    return None


async def _fetch_news_finnhub(ticker: str = None, limit: int = 20) -> Optional[list[dict]]:
    if not settings.FINNHUB_API_KEY:
        return None
    try:
        client = _get_client()
        if ticker:
            from datetime import datetime, timedelta
            today = datetime.now().strftime("%Y-%m-%d")
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            resp = await client.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": ticker,
                    "from": week_ago,
                    "to": today,
                    "token": settings.FINNHUB_API_KEY,
                },
            )
        else:
            resp = await client.get(
                "https://finnhub.io/api/v1/news",
                params={"category": "general", "token": settings.FINNHUB_API_KEY},
            )

        if resp.status_code == 200:
            data = resp.json()
            if data:
                return [
                    {
                        "headline": item.get("headline", ""),
                        "summary": item.get("summary", ""),
                        "source": item.get("source", ""),
                        "url": item.get("url", ""),
                        "image_url": item.get("image", ""),
                        "ticker": ticker or "",
                        "published_at": item.get("datetime", ""),
                    }
                    for item in data[:limit]
                ]
    except Exception:
        pass
    return None


# ── Earnings Calendar ────────────────────────────────────────────────────────

async def get_earnings_calendar(from_date: str = None, to_date: str = None) -> list[dict]:
    """Get upcoming earnings calendar."""
    cache_key = f"earnings_cal:{from_date}:{to_date}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    result = await _fetch_earnings_fmp(from_date, to_date)
    if not result:
        result = await _fetch_earnings_finnhub(from_date, to_date)
    if not result:
        result = []

    _cache.set(cache_key, result, CHART_TTL)
    return result


async def _fetch_earnings_fmp(from_date: str = None, to_date: str = None) -> Optional[list[dict]]:
    if not settings.FMP_API_KEY:
        return None
    try:
        client = _get_client()
        params = {"apikey": settings.FMP_API_KEY}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        resp = await client.get(
            "https://financialmodelingprep.com/api/v3/earning_calendar",
            params=params,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return [
                    {
                        "ticker": item.get("symbol", ""),
                        "company_name": "",
                        "report_date": item.get("date", ""),
                        "fiscal_period": item.get("fiscalDateEnding", ""),
                        "eps_estimate": item.get("epsEstimated"),
                        "revenue_estimate": item.get("revenueEstimated"),
                        "eps_actual": item.get("eps"),
                        "revenue_actual": item.get("revenue"),
                        "time": item.get("time", ""),  # bmo, amc
                    }
                    for item in data
                ]
    except Exception:
        pass
    return None


async def _fetch_earnings_finnhub(from_date: str = None, to_date: str = None) -> Optional[list[dict]]:
    if not settings.FINNHUB_API_KEY:
        return None
    try:
        client = _get_client()
        params = {"token": settings.FINNHUB_API_KEY}
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        resp = await client.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params=params,
        )
        if resp.status_code == 200:
            data = resp.json()
            earnings = data.get("earningsCalendar", [])
            return [
                {
                    "ticker": item.get("symbol", ""),
                    "company_name": "",
                    "report_date": item.get("date", ""),
                    "fiscal_period": f"Q{item.get('quarter', '')} {item.get('year', '')}",
                    "eps_estimate": item.get("epsEstimate"),
                    "revenue_estimate": item.get("revenueEstimate"),
                    "eps_actual": item.get("epsActual"),
                    "revenue_actual": item.get("revenueActual"),
                    "time": item.get("hour", ""),
                }
                for item in earnings
            ]
    except Exception:
        pass
    return None
