"""
utils/helpers.py - Shared utilities used across modules.

Small, pure helper functions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger with a clean format.

    Usage:
        logger = get_logger(__name__)
        logger.info("Crawled 42 articles")
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        fmt = logging.Formatter(
            "%(asctime)s | %(name)-24s | %(levelname)-7s | %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def save_articles_json(articles: list[dict], path: Path) -> None:
    """Persist a list of article dicts to a JSON file.

    Each article should have at minimum:
        title, link, published, source, text
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2, default=str)


def load_articles_json(path: Path) -> list[dict]:
    """Load articles from a JSON file. Returns [] if file is missing."""
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def articles_to_dataframe(articles: list[dict]) -> pd.DataFrame:
    """Convert article dicts to a DataFrame with proper datetime parsing."""
    df = pd.DataFrame(articles)
    if "published" in df.columns:
        df["published"] = pd.to_datetime(df["published"], errors="coerce", utc=True)
    return df


def utc_now() -> datetime:
    """Timezone-aware UTC now — avoids naive-datetime pitfalls."""
    return datetime.now(timezone.utc)


def hours_since(dt: datetime) -> float:
    """Hours elapsed since *dt*. Returns a large number if dt is None/NaT."""
    if dt is None or pd.isna(dt):
        return 9999.0
    now = utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max((now - dt).total_seconds() / 3600.0, 0.0)
