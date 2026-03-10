"""
Finhaus — Alpaca Brokerage Service.

Integrates with Alpaca Trading API for live portfolio data:
account info, positions, portfolio history, and orders.
"""

from typing import Optional
import httpx
from app.config import get_settings

settings = get_settings()

_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Get configured Alpaca HTTP client."""
    global _client
    if _client is None or _client.is_closed:
        base_url = settings.ALPACA_BASE_URL
        _client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "APCA-API-KEY-ID": settings.ALPACA_API_KEY,
                "APCA-API-SECRET-KEY": settings.ALPACA_SECRET_KEY,
            },
            timeout=10.0,
        )
    return _client


async def close_client():
    global _client
    if _client and not _client.is_closed:
        await _client.aclose()
        _client = None


def is_configured() -> bool:
    """Check if Alpaca credentials are set."""
    return bool(settings.ALPACA_API_KEY and settings.ALPACA_SECRET_KEY)


async def get_account() -> Optional[dict]:
    """Get Alpaca account info (equity, buying power, etc.)."""
    if not is_configured():
        return None
    try:
        client = _get_client()
        resp = await client.get("/v2/account")
        if resp.status_code == 200:
            data = resp.json()
            return {
                "account_id": data.get("id", ""),
                "status": data.get("status", ""),
                "equity": float(data.get("equity", 0)),
                "buying_power": float(data.get("buying_power", 0)),
                "cash": float(data.get("cash", 0)),
                "portfolio_value": float(data.get("portfolio_value", 0)),
                "last_equity": float(data.get("last_equity", 0)),
                "long_market_value": float(data.get("long_market_value", 0)),
                "short_market_value": float(data.get("short_market_value", 0)),
                "initial_margin": float(data.get("initial_margin", 0)),
                "maintenance_margin": float(data.get("maintenance_margin", 0)),
                "daytrade_count": int(data.get("daytrade_count", 0)),
                "pattern_day_trader": data.get("pattern_day_trader", False),
                "currency": data.get("currency", "USD"),
            }
    except Exception:
        pass
    return None


async def get_positions() -> list[dict]:
    """Get all open positions with unrealized P&L."""
    if not is_configured():
        return []
    try:
        client = _get_client()
        resp = await client.get("/v2/positions")
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "ticker": pos.get("symbol", ""),
                    "qty": float(pos.get("qty", 0)),
                    "side": pos.get("side", "long"),
                    "avg_entry_price": float(pos.get("avg_entry_price", 0)),
                    "current_price": float(pos.get("current_price", 0)),
                    "market_value": float(pos.get("market_value", 0)),
                    "cost_basis": float(pos.get("cost_basis", 0)),
                    "unrealized_pl": float(pos.get("unrealized_pl", 0)),
                    "unrealized_plpc": float(pos.get("unrealized_plpc", 0)),
                    "unrealized_intraday_pl": float(pos.get("unrealized_intraday_pl", 0)),
                    "unrealized_intraday_plpc": float(pos.get("unrealized_intraday_plpc", 0)),
                    "change_today": float(pos.get("change_today", 0)),
                    "asset_class": pos.get("asset_class", "us_equity"),
                }
                for pos in data
            ]
    except Exception:
        pass
    return []


async def get_portfolio_history(period: str = "1M", timeframe: str = "1D") -> Optional[dict]:
    """
    Get portfolio equity curve over time.
    period: 1D, 1W, 1M, 3M, 1A, all
    timeframe: 1Min, 5Min, 15Min, 1H, 1D
    """
    if not is_configured():
        return None
    try:
        client = _get_client()
        resp = await client.get(
            "/v2/account/portfolio/history",
            params={"period": period, "timeframe": timeframe},
        )
        if resp.status_code == 200:
            data = resp.json()
            timestamps = data.get("timestamp", [])
            equity = data.get("equity", [])
            profit_loss = data.get("profit_loss", [])
            profit_loss_pct = data.get("profit_loss_pct", [])

            return {
                "timestamps": timestamps,
                "equity": equity,
                "profit_loss": profit_loss,
                "profit_loss_pct": profit_loss_pct,
                "base_value": data.get("base_value", 0),
                "timeframe": data.get("timeframe", timeframe),
            }
    except Exception:
        pass
    return None


async def get_orders(status: str = "all", limit: int = 20) -> list[dict]:
    """Get recent orders. status: open, closed, all."""
    if not is_configured():
        return []
    try:
        client = _get_client()
        resp = await client.get(
            "/v2/orders",
            params={"status": status, "limit": limit, "direction": "desc"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return [
                {
                    "id": order.get("id", ""),
                    "ticker": order.get("symbol", ""),
                    "side": order.get("side", ""),
                    "type": order.get("type", ""),
                    "qty": order.get("qty", ""),
                    "filled_qty": order.get("filled_qty", ""),
                    "filled_avg_price": order.get("filled_avg_price"),
                    "status": order.get("status", ""),
                    "submitted_at": order.get("submitted_at", ""),
                    "filled_at": order.get("filled_at"),
                    "limit_price": order.get("limit_price"),
                    "stop_price": order.get("stop_price"),
                    "time_in_force": order.get("time_in_force", ""),
                }
                for order in data
            ]
    except Exception:
        pass
    return []
