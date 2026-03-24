"""
crawler/rss_crawler.py — RSS feed crawler with full-text extraction.

Fetches articles from curated RSS feeds, extracts full article text
using newspaper3k, deduplicates by URL, and returns clean article dicts.

"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import time

import feedparser
from dateutil import parser as dateutil_parser
from newspaper import Article, Config

from config.settings import (
    RSS_FEEDS,
    SOURCE_NAME_OVERRIDES,
    CRAWL_TIMEOUT_SECONDS,
    ARTICLES_PATH,
    MAX_ARTICLE_AGE_DAYS,
)
from utils.helpers import get_logger, save_articles_json

logger = get_logger(__name__)

# Minimum article length (chars) to keep.
MIN_TEXT_LENGTH = 100
MAX_EXTRACTION_WORKERS = 8


# Single-article helpers 

def _parse_published(entry) -> str:
    """Extract a UTC ISO-format publish date from a feed entry.

    feedparser populates `published_parsed` (a time.struct_time) on most
    entries, but some feeds use `updated_parsed` or nothing at all.
    We try multiple fields, fall back to "now" so downstream code always
    has a valid datetime string.
    """
    # Try the pre-parsed struct_time fields first (most reliable)
    for field in ("published_parsed", "updated_parsed"):
        struct = getattr(entry, field, None)
        if struct is not None:
            try:
                dt = datetime(*struct[:6]).replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

    # Fall back to raw string parsing (handles "Mon, 10 Feb 2026..." etc.)
    for field in ("published", "updated"):
        raw = getattr(entry, field, None)
        if raw:
            try:
                dt = dateutil_parser.parse(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass

    # Last resort, use current time
    return datetime.now(timezone.utc).isoformat()


def _is_within_days(published_iso: str, max_age_days: int) -> bool:
    """Return True when a publish date is within the requested age window."""
    try:
        published_dt = dateutil_parser.parse(published_iso)
    except Exception:
        return False

    if published_dt.tzinfo is None:
        published_dt = published_dt.replace(tzinfo=timezone.utc)

    age = datetime.now(timezone.utc) - published_dt.astimezone(timezone.utc)
    return age.days <= max_age_days


def extract_full_text(url: str) -> str:
    """
    Download and parse an article URL to extract the body text using newspaper3k.
    """
    try:
        config = Config()
        config.request_timeout = CRAWL_TIMEOUT_SECONDS
        config.fetch_images = False

        article = Article(url, config=config)
        article.download()
        article.parse()
        return article.text.strip()
    except Exception as e:
        logger.debug(f"Text extraction failed for {url}: {e}")
        return ""


# Per-feed crawler 

def fetch_feed(feed_url: str) -> tuple[list[dict], dict]:
    """Parse a single RSS feed and return raw article dicts + feed stats.

    Each dict contains: title, link, published (ISO string), source.
    Text is NOT extracted here — that's a separate step so we can
    skip duplicates before doing expensive HTTP requests.

    Returns:
        (articles, stats) where stats has keys:
            source, url, article_count, status, elapsed_seconds, error
    """
    t0 = time.time()
    stats = {"url": feed_url, "source": feed_url, "article_count": 0,
             "status": "success", "elapsed_seconds": 0.0, "error": None}

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.warning(f"Failed to parse feed {feed_url}: {e}")
        stats.update(status="failed", error=str(e),
                     elapsed_seconds=round(time.time() - t0, 2))
        return [], stats
    # Override the source name, this was the case for Amazon.
    source = SOURCE_NAME_OVERRIDES.get(feed_url, getattr(feed.feed, "title", feed_url))
    stats["source"] = source
    articles = []

    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()

        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link,
            "published": _parse_published(entry),
            "source": source,
        })

    stats["article_count"] = len(articles)
    stats["elapsed_seconds"] = round(time.time() - t0, 2)
    logger.info(f"  {source:<30s} → {len(articles)} entries")
    return articles, stats


# Main crawler 

def crawl_all_feeds(
    max_age_days: int | None = None,
    existing_urls: set[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Crawl all configured RSS feeds and return deduplicated articles + feed stats.

    Pipeline:
        1. Fetch entries from every RSS feed
        2. Deduplicate by URL (within this run + against *existing_urls*)
        3. Drop articles older than *max_age_days*
        4. Extract full text for each unique, new article
        5. Drop articles with insufficient text

    Args:
        max_age_days: Keep only articles from the last N days.
            Example: 7 keeps only the last week. If None, no date filter.
        existing_urls: URLs already stored in the database. Articles with
            these URLs are skipped before the expensive text-extraction step.

    Returns:
        (articles, feed_stats) — articles ready for filtering/indexing,
        and per-feed stats for the health dashboard.
    """
    logger.info(f"Crawling {len(RSS_FEEDS)} RSS feeds ...")

    raw_articles = []
    feed_stats = []
    for url in RSS_FEEDS:
        articles_batch, stats = fetch_feed(url)
        raw_articles.extend(articles_batch)
        feed_stats.append(stats)

    logger.info(f"Raw entries collected: {len(raw_articles)}")

    # Deduplicate by URL (within this run + against DB)
    seen_urls: set[str] = set(existing_urls or ())
    unique_articles = []
    for article in raw_articles:
        if article["link"] not in seen_urls:
            seen_urls.add(article["link"])
            unique_articles.append(article)

    n_skipped = len(raw_articles) - len(unique_articles)
    logger.info(
        f"After dedup: {len(unique_articles)} new articles "
        f"({n_skipped} skipped — duplicates or already in DB)"
    )

    # Drop articles older than max_age_days (7 days by default) before expensive page extraction.
    if max_age_days is not None:
        before = len(unique_articles)
        unique_articles = [
            a for a in unique_articles if _is_within_days(a.get("published", ""), max_age_days)
        ]
        if before != len(unique_articles):
            logger.info(f"Age filter: dropped {before - len(unique_articles)} articles older than {max_age_days}d")

    # Extract full text
    logger.info(f"Extracting full text for {len(unique_articles)} articles")
    with ThreadPoolExecutor(max_workers=MAX_EXTRACTION_WORKERS) as executor:
        extracted_texts = list(executor.map(
            extract_full_text,
            [article["link"] for article in unique_articles],
        ))

    for article, text in zip(unique_articles, extracted_texts):
        article["text"] = text

    # Drop articles with insufficient text
    full_articles = [
        a for a in unique_articles if len(a.get("text", "")) >= MIN_TEXT_LENGTH
    ]
    logger.info(f"Final article count: {len(full_articles)}")

    return full_articles, feed_stats


if __name__ == "__main__":
    """Run the full crawler pipeline and save results to JSON."""
    # Ask if user wants to delete existing articles file before crawling
    if os.path.exists(ARTICLES_PATH):
        response = input(
            f"An articles file already exists at {ARTICLES_PATH}. "
            "Do you want to delete it before crawling? (y/n): "
        ).strip().lower()
        if response == "y":
            os.remove(ARTICLES_PATH)
            logger.info(f"Deleted existing file at {ARTICLES_PATH}")
        else:
            logger.info("Keeping existing file. New articles will be added to it.")
    articles, _feed_stats = crawl_all_feeds(max_age_days=MAX_ARTICLE_AGE_DAYS)

    if articles:
        save_articles_json(articles, ARTICLES_PATH)
        logger.info(f"Saved {len(articles)} articles at {ARTICLES_PATH}")
    else:
        logger.warning("No articles crawled. Check your internet connection or feed URLs.")
