"""
Hawker — Pydantic response/request schemas.

These define the API contract and the structured JSON output format.
"""

from __future__ import annotations
from datetime import date, datetime
from pydantic import BaseModel, Field


# ── Key Metrics ──────────────────────────────────────────────────────────────

class KeyMetrics(BaseModel):
    revenue: str | None = None
    revenue_surprise: str | None = None
    eps: str | None = None
    eps_surprise: str | None = None
    gross_margin: str | None = None
    operating_margin: str | None = None
    operating_cash_flow: str | None = None
    free_cash_flow: str | None = None
    guidance_revenue_next_q: str | None = None
    guidance_eps_next_q: str | None = None


# ── Analyst Action ───────────────────────────────────────────────────────────

class AnalystAction(BaseModel):
    firm: str
    action: str         # Upgrade, Downgrade, Initiate, Reiterate
    rating_to: str | None = None
    price_target: float | None = None


class AnalystSentiment(BaseModel):
    consensus: str | None = None           # Overweight, Buy, Hold, Sell
    avg_price_target: str | None = None
    recent_changes: list[AnalystAction] = []


# ── Intelligence Item — The Core Output ──────────────────────────────────────

class IntelligenceItemSchema(BaseModel):
    """The structured JSON output per the spec."""
    company: str
    ticker: str
    date: str
    source_type: str
    key_metrics: KeyMetrics | None = None
    positive_catalysts: list[str] = []
    negative_risks: list[str] = []
    analyst_sentiment: AnalystSentiment | None = None
    actionable_summary: list[str] = Field(default=[], max_length=5)
    impact_score: float = 0.0
    tags: list[str] = []


class IntelligenceItemResponse(BaseModel):
    """API response wrapper for a single intelligence item."""
    id: int
    company_id: int
    source_type: str
    structured_output: IntelligenceItemSchema
    impact_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Feed Response ────────────────────────────────────────────────────────────

class FeedResponse(BaseModel):
    """Paginated feed of intelligence items, ranked by impact."""
    items: list[IntelligenceItemResponse]
    total: int
    page: int
    page_size: int


# ── Company Schemas ──────────────────────────────────────────────────────────

class CompanyBase(BaseModel):
    ticker: str
    name: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    logo_url: str | None = None


class CompanyResponse(CompanyBase):
    id: int
    description: str | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class CompanyDeepDive(BaseModel):
    """Full company view with latest intelligence, earnings, ratings, and news."""
    company: CompanyResponse
    latest_intelligence: list[IntelligenceItemResponse] = []
    recent_earnings: list[EarningsReportResponse] = []
    recent_ratings: list[AnalystRatingResponse] = []
    recent_news: list[NewsItemResponse] = []


# ── Earnings ─────────────────────────────────────────────────────────────────

class EarningsReportResponse(BaseModel):
    id: int
    company_id: int
    report_date: date
    fiscal_period: str | None = None
    revenue: float | None = None
    eps: float | None = None
    revenue_estimate: float | None = None
    eps_estimate: float | None = None
    revenue_surprise_pct: float | None = None
    eps_surprise: float | None = None
    gross_margin: float | None = None
    guidance: dict | None = None

    model_config = {"from_attributes": True}


class EarningsCalendarItem(BaseModel):
    ticker: str
    company_name: str
    report_date: date
    fiscal_period: str | None = None
    eps_estimate: float | None = None
    revenue_estimate: float | None = None


# ── Analyst Ratings ──────────────────────────────────────────────────────────

class AnalystRatingResponse(BaseModel):
    id: int
    company_id: int
    firm: str
    action: str
    rating_from: str | None = None
    rating_to: str | None = None
    price_target: float | None = None
    prev_price_target: float | None = None
    action_date: date

    model_config = {"from_attributes": True}


# ── News ─────────────────────────────────────────────────────────────────────

class NewsItemResponse(BaseModel):
    id: int
    company_id: int | None = None
    headline: str
    summary: str | None = None
    source: str | None = None
    category: str | None = None
    url: str | None = None
    image_url: str | None = None
    sentiment_score: float | None = None
    published_at: datetime

    model_config = {"from_attributes": True}


# ── Watchlist ────────────────────────────────────────────────────────────────

class WatchlistCreate(BaseModel):
    name: str
    tickers: list[str] = []


class WatchlistResponse(BaseModel):
    id: int
    name: str
    tickers: list[CompanyBase] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class WatchlistAddTicker(BaseModel):
    ticker: str
