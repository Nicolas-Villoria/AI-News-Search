"""
crawler/rss_crawler.py — RSS feed crawler with full-text extraction.

Fetches articles from curated RSS feeds, extracts full article text
using newspaper3k, deduplicates by URL, and returns clean article dicts.

"""

from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateutil_parser
from newspaper import Article

from config.settings import RSS_FEEDS, CRAWL_TIMEOUT_SECONDS, ARTICLES_PATH
from utils.helpers import get_logger, save_articles_json

logger = get_logger(__name__)

# Minimum article length (chars) to keep.
MIN_TEXT_LENGTH = 100


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


def extract_full_text(url: str) -> str:
    """
    Download and parse an article URL to extract the body text using newspaper3k.
    """
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text.strip()
    except Exception as e:
        logger.debug(f"Text extraction failed for {url}: {e}")
        return ""


# Per-feed crawler 

def fetch_feed(feed_url: str) -> list[dict]:
    """Parse a single RSS feed and return raw article dicts.

    Each dict contains: title, link, published (ISO string), source.
    Text is NOT extracted here — that's a separate step so we can
    skip duplicates before doing expensive HTTP requests.
    """
    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        logger.warning(f"Failed to parse feed {feed_url}: {e}")
        return []

    # Use the feed's own title as the source name, e.g. "TechCrunch"
    source = getattr(feed.feed, "title", feed_url)
    articles = []

    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()

        # Skip entries missing essential fields
        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link,
            "published": _parse_published(entry),
            "source": source,
        })

    logger.info(f"  {source:<30s} → {len(articles)} entries")
    return articles


# Main crawler 

def crawl_all_feeds(feeds: list[str] | None = None) -> list[dict]:
    """Crawl all configured RSS feeds and return deduplicated articles.

    Pipeline:
        1. Fetch entries from every RSS feed
        2. Deduplicate by URL
        3. Extract full text for each unique article
        4. Drop articles with insufficient text

    Args:
        feeds: Override the default feed list (useful for testing).

    Returns:
        List of article dicts ready for filtering / indexing.
        Keys: title, link, published, source, text
    """
    feeds = feeds or RSS_FEEDS
    logger.info(f"Crawling {len(feeds)} RSS feeds …")

    # Gather all entries
    raw_articles = []
    for url in feeds:
        raw_articles.extend(fetch_feed(url))

    logger.info(f"Raw entries collected: {len(raw_articles)}")

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_articles = []
    for article in raw_articles:
        if article["link"] not in seen_urls:
            seen_urls.add(article["link"])
            unique_articles.append(article)

    logger.info(
        f"After dedup: {len(unique_articles)} "
        f"(removed {len(raw_articles) - len(unique_articles)} duplicates)"
    )

    # Extract full text
    logger.info("Extracting full article text (this may take a minute) …")
    for i, article in enumerate(unique_articles, 1):
        article["text"] = extract_full_text(article["link"])
        if i % 10 == 0 or i == len(unique_articles):
            logger.info(f"  Extracted {i}/{len(unique_articles)}")

    # Drop articles with insufficient text
    full_articles = [
        a for a in unique_articles if len(a.get("text", "")) >= MIN_TEXT_LENGTH
    ]
    dropped = len(unique_articles) - len(full_articles)
    logger.info(
        f"Final article count: {len(full_articles)} "
        f"(dropped {dropped} with text < {MIN_TEXT_LENGTH} chars)"
    )

    return full_articles


if __name__ == "__main__":
    """Quick test: crawl all feeds, save to data/articles.json, print stats."""
    articles = crawl_all_feeds()

    if articles:
        save_articles_json(articles, ARTICLES_PATH)
        logger.info(f"Saved {len(articles)} articles at {ARTICLES_PATH}")
    else:
        logger.warning("No articles crawled. Check your internet connection or feed URLs.")
