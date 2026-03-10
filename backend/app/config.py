"""
Finhaus — Central configuration.

All settings are loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # App
    APP_NAME: str = "Finhaus"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hawker"

    # API Keys — Primary data providers
    FMP_API_KEY: str = ""              # Financial Modeling Prep
    FINNHUB_API_KEY: str = ""          # Finnhub.io

    # API Keys — Fallback data providers
    ALPHA_VANTAGE_API_KEY: str = ""    # Alpha Vantage (fallback)

    # Alpaca Brokerage
    ALPACA_API_KEY: str = ""           # Alpaca API key
    ALPACA_SECRET_KEY: str = ""        # Alpaca secret key
    ALPACA_BASE_URL: str = "https://paper-api.alpaca.markets"  # paper trading by default

    # OpenAI (for intelligence summarization)
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 1024
    OPENAI_TEMPERATURE: float = 0.3

    # SEC
    SEC_USER_AGENT: str = ""

    # Default tickers for watchlist
    DEFAULT_TICKERS: list[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA",
        "META", "TSLA", "JPM", "V", "WMT",
    ]

    # Data Ingestion
    INGESTION_INTERVAL_MINUTES: int = 60

    # Scoring Weights
    W_SURPRISE: float = 0.30
    W_GUIDANCE: float = 0.20
    W_ANALYST: float = 0.20
    W_SENTIMENT: float = 0.15
    W_MAGNITUDE: float = 0.15

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
