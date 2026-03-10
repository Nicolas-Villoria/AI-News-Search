"""
Hawker — SQLAlchemy ORM models.
"""

from datetime import datetime, date
from sqlalchemy import (
    Column, Integer, String, Float, Text, Date, DateTime,
    ForeignKey, JSON, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


# ── Company ──────────────────────────────────────────────────────────────────

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    market_cap = Column(Float)
    description = Column(Text)
    logo_url = Column(String(512))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    earnings = relationship("EarningsReport", back_populates="company", cascade="all, delete-orphan")
    filings = relationship("SECFiling", back_populates="company", cascade="all, delete-orphan")
    analyst_ratings = relationship("AnalystRating", back_populates="company", cascade="all, delete-orphan")
    news_items = relationship("NewsItem", back_populates="company", cascade="all, delete-orphan")
    intelligence_items = relationship("IntelligenceItem", back_populates="company", cascade="all, delete-orphan")


# ── Earnings Report ──────────────────────────────────────────────────────────

class EarningsReport(Base):
    __tablename__ = "earnings_reports"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    report_date = Column(Date, nullable=False)
    fiscal_period = Column(String(20))  # e.g., "Q1 2026"

    # Actual metrics
    revenue = Column(Float)
    eps = Column(Float)
    gross_margin = Column(Float)
    operating_margin = Column(Float)
    net_income = Column(Float)
    operating_cash_flow = Column(Float)
    free_cash_flow = Column(Float)

    # Estimates (consensus)
    revenue_estimate = Column(Float)
    eps_estimate = Column(Float)

    # Surprise calculations
    revenue_surprise_pct = Column(Float)
    eps_surprise = Column(Float)

    # Guidance
    guidance = Column(JSON)  # {"revenue_low": ..., "revenue_high": ..., "eps_low": ..., "eps_high": ...}

    # Raw data blob
    raw_data = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="earnings")

    __table_args__ = (
        UniqueConstraint("company_id", "report_date", name="uq_earnings_company_date"),
        Index("ix_earnings_date", "report_date"),
    )


# ── SEC Filing ───────────────────────────────────────────────────────────────

class SECFiling(Base):
    __tablename__ = "sec_filings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    filing_type = Column(String(20), nullable=False)  # 10-K, 10-Q, 8-K
    filed_date = Column(Date, nullable=False)
    accession_number = Column(String(50), unique=True)
    summary = Column(Text)
    edgar_url = Column(String(512))
    extracted_metrics = Column(JSON)

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="filings")

    __table_args__ = (
        Index("ix_filings_type_date", "filing_type", "filed_date"),
    )


# ── Analyst Rating ───────────────────────────────────────────────────────────

class AnalystRating(Base):
    __tablename__ = "analyst_ratings"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    firm = Column(String(100), nullable=False)
    analyst_name = Column(String(100))
    action = Column(String(30), nullable=False)   # Upgrade, Downgrade, Initiate, Reiterate
    rating_from = Column(String(30))               # e.g., "Hold"
    rating_to = Column(String(30))                 # e.g., "Buy"
    price_target = Column(Float)
    prev_price_target = Column(Float)
    action_date = Column(Date, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="analyst_ratings")

    __table_args__ = (
        Index("ix_analyst_date", "action_date"),
    )


# ── News Item ────────────────────────────────────────────────────────────────

class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)  # nullable for macro news
    headline = Column(String(500), nullable=False)
    summary = Column(Text)
    source = Column(String(100))
    category = Column(String(50))   # company, sector, macro
    url = Column(String(512), unique=True)
    image_url = Column(String(512))
    sentiment_score = Column(Float)  # -1.0 to 1.0
    published_at = Column(DateTime, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="news_items")

    __table_args__ = (
        Index("ix_news_published", "published_at"),
    )


# ── Intelligence Item (Processed Output) ────────────────────────────────────

class IntelligenceItem(Base):
    """The core output: a fully processed, structured intelligence item
    conforming to the JSON schema in the implementation plan."""
    __tablename__ = "intelligence_items"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    source_type = Column(String(30), nullable=False)  # earnings_report, sec_filing, analyst_rating, news
    source_id = Column(Integer)  # FK to the raw source row

    # The full structured JSON output
    structured_output = Column(JSON, nullable=False)
    impact_score = Column(Float, nullable=False, default=0.0)
    tags = Column(JSON)  # ["earnings_beat", "guidance_raise", ...]

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="intelligence_items")

    __table_args__ = (
        Index("ix_intel_impact", "impact_score"),
        Index("ix_intel_source_type", "source_type"),
        Index("ix_intel_created", "created_at"),
    )


# ── Watchlist ────────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)  # Placeholder for auth
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("WatchlistItem", back_populates="watchlist", cascade="all, delete-orphan")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(Integer, primary_key=True, index=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    watchlist = relationship("Watchlist", back_populates="items")
    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("watchlist_id", "company_id", name="uq_watchlist_company"),
    )


# ── Portfolio ────────────────────────────────────────────────────────────────

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    source = Column(String(20), nullable=False, default="manual")  # "alpaca" | "manual"
    created_at = Column(DateTime, default=datetime.utcnow)

    holdings = relationship("PortfolioHolding", back_populates="portfolio", cascade="all, delete-orphan")


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    ticker = Column(String(10), nullable=False)
    shares = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="holdings")
