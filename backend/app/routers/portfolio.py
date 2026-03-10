"""
Finhaus — Portfolio router.

Alpaca brokerage integration + manual portfolio fallback.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.database import get_db
from app.models.models import Portfolio, PortfolioHolding
from app.services import alpaca_service, market_data

router = APIRouter()

DEFAULT_USER_ID = "default_user"


# ── Alpaca Brokerage Endpoints ───────────────────────────────────────────────

@router.get("/alpaca/status")
async def alpaca_status():
    """Check if Alpaca is configured and connected."""
    if not alpaca_service.is_configured():
        return {"connected": False, "message": "Alpaca API keys not configured"}
    account = await alpaca_service.get_account()
    if account:
        return {"connected": True, "account_status": account.get("status", ""), "equity": account.get("equity", 0)}
    return {"connected": False, "message": "Failed to connect to Alpaca"}


@router.get("/alpaca/account")
async def get_alpaca_account():
    """Get Alpaca account summary."""
    if not alpaca_service.is_configured():
        raise HTTPException(status_code=400, detail="Alpaca not configured. Set ALPACA_API_KEY and ALPACA_SECRET_KEY.")
    account = await alpaca_service.get_account()
    if not account:
        raise HTTPException(status_code=502, detail="Failed to fetch Alpaca account")
    return account


@router.get("/alpaca/positions")
async def get_alpaca_positions():
    """Get live brokerage positions with P&L."""
    if not alpaca_service.is_configured():
        raise HTTPException(status_code=400, detail="Alpaca not configured")
    return await alpaca_service.get_positions()


@router.get("/alpaca/history")
async def get_alpaca_history(
    period: str = Query("1M", description="Period: 1D, 1W, 1M, 3M, 1A, all"),
    timeframe: str = Query("1D", description="Timeframe: 1Min, 5Min, 15Min, 1H, 1D"),
):
    """Get portfolio equity curve over time."""
    if not alpaca_service.is_configured():
        raise HTTPException(status_code=400, detail="Alpaca not configured")
    history = await alpaca_service.get_portfolio_history(period, timeframe)
    if not history:
        raise HTTPException(status_code=502, detail="Failed to fetch portfolio history")
    return history


@router.get("/alpaca/orders")
async def get_alpaca_orders(
    status: str = Query("all", description="Order status: open, closed, all"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get recent orders."""
    if not alpaca_service.is_configured():
        raise HTTPException(status_code=400, detail="Alpaca not configured")
    return await alpaca_service.get_orders(status, limit)


# ── Manual Portfolio Endpoints ───────────────────────────────────────────────

@router.get("/manual")
async def list_manual_portfolios(db: AsyncSession = Depends(get_db)):
    """List all manual portfolios."""
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.user_id == DEFAULT_USER_ID,
            Portfolio.source == "manual",
        )
    )
    portfolios = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "source": p.source,
            "created_at": p.created_at,
        }
        for p in portfolios
    ]


@router.post("/manual")
async def create_manual_portfolio(
    name: str = Query(..., description="Portfolio name"),
    db: AsyncSession = Depends(get_db),
):
    """Create a manual portfolio."""
    portfolio = Portfolio(
        user_id=DEFAULT_USER_ID,
        name=name,
        source="manual",
    )
    db.add(portfolio)
    await db.flush()
    return {"id": portfolio.id, "name": portfolio.name, "source": "manual"}


@router.post("/manual/{portfolio_id}/holdings")
async def add_manual_holding(
    portfolio_id: int,
    ticker: str = Query(...),
    shares: float = Query(..., gt=0),
    avg_cost: float = Query(..., gt=0),
    db: AsyncSession = Depends(get_db),
):
    """Add a holding to a manual portfolio."""
    pf_q = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    pf = pf_q.scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holding = PortfolioHolding(
        portfolio_id=portfolio_id,
        ticker=ticker.upper(),
        shares=shares,
        avg_cost=avg_cost,
    )
    db.add(holding)
    await db.flush()
    return {"id": holding.id, "ticker": holding.ticker, "shares": shares, "avg_cost": avg_cost}


@router.get("/manual/{portfolio_id}/summary")
async def get_manual_portfolio_summary(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get manual portfolio summary with live prices."""
    pf_q = await db.execute(select(Portfolio).where(Portfolio.id == portfolio_id))
    pf = pf_q.scalar_one_or_none()
    if not pf:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    holdings_q = await db.execute(
        select(PortfolioHolding).where(PortfolioHolding.portfolio_id == portfolio_id)
    )
    holdings = holdings_q.scalars().all()

    if not holdings:
        return {
            "portfolio": {"id": pf.id, "name": pf.name},
            "holdings": [],
            "total_value": 0,
            "total_cost": 0,
            "total_pnl": 0,
            "total_pnl_pct": 0,
        }

    # Fetch live prices
    tickers = [h.ticker for h in holdings]
    quotes = await market_data.get_batch_quotes(tickers)
    price_map = {q["ticker"]: q["price"] for q in quotes}

    enriched_holdings = []
    total_value = 0
    total_cost = 0

    for h in holdings:
        price = price_map.get(h.ticker, 0)
        value = h.shares * price
        cost = h.shares * h.avg_cost
        pnl = value - cost
        pnl_pct = (pnl / cost * 100) if cost > 0 else 0

        enriched_holdings.append({
            "id": h.id,
            "ticker": h.ticker,
            "shares": h.shares,
            "avg_cost": h.avg_cost,
            "current_price": price,
            "market_value": round(value, 2),
            "cost_basis": round(cost, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
        })
        total_value += value
        total_cost += cost

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

    return {
        "portfolio": {"id": pf.id, "name": pf.name},
        "holdings": enriched_holdings,
        "total_value": round(total_value, 2),
        "total_cost": round(total_cost, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": round(total_pnl_pct, 2),
    }


@router.delete("/manual/{portfolio_id}/holdings/{holding_id}")
async def remove_manual_holding(
    portfolio_id: int,
    holding_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a holding from a manual portfolio."""
    await db.execute(
        delete(PortfolioHolding).where(
            PortfolioHolding.id == holding_id,
            PortfolioHolding.portfolio_id == portfolio_id,
        )
    )
    return {"status": "removed"}
