"""
pipeline/run_pipeline.py — End-to-end data pipeline orchestrator.

Runs the full ingestion pipeline in order and collects timing /
success metrics for the Pipeline Health dashboard.

Writes to both PostgreSQL (primary) and flat files (legacy fallback)
so the API continues to work during the migration.
"""

import json
import time
from collections import Counter
from datetime import datetime, timezone

from crawler.rss_crawler import crawl_all_feeds
from filter.ai_filter import filter_articles
from indexer.build_index import build_and_save_index, embed_and_store_articles
from config.settings import ARTICLES_PATH, MAX_ARTICLE_AGE_DAYS, PIPELINE_STATS_PATH
from utils.helpers import get_logger, save_articles_json

logger = get_logger(__name__)


def _get_db_session():
    """Try to open a DB session. Returns None if the database is unavailable."""
    try:
        from db.database import SessionLocal
        db = SessionLocal()
        db.connection()
        return db
    except Exception as e:
        logger.warning(f"Database unavailable, running file-only pipeline: {e}")
        return None


def _save_pipeline_run(db, stats: dict) -> None:
    """Write or update the pipeline_runs row in PostgreSQL."""
    from db.models import PipelineRun
    from dateutil import parser as dateutil_parser

    started = dateutil_parser.parse(stats["started_at"])
    finished = (
        dateutil_parser.parse(stats["finished_at"]) if stats.get("finished_at") else None
    )

    run = PipelineRun(
        started_at=started,
        completed_at=finished,
        status=stats["status"],
        stats=stats,
    )
    db.add(run)
    db.commit()
    logger.info("Pipeline run saved to PostgreSQL")


def run_pipeline() -> dict:
    """Execute the full data pipeline: crawl -> filter -> embed -> store.

    Writes to PostgreSQL when the database is available, and always
    writes legacy flat files so the existing API keeps working.

    Returns:
        A stats dict with timing, counts, and per-feed health info.
    """
    pipeline_start = time.time()

    stats: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
        "total_seconds": 0.0,
        "crawl": {"articles": 0, "seconds": 0.0},
        "filter": {"input": 0, "output": 0, "pass_rate": 0.0, "seconds": 0.0},
        "index": {"vectors": 0, "avg_embed_seconds": 0.0, "seconds": 0.0},
        "feed_stats": [],
        "status": "running",
        "error": None,
    }

    db = _get_db_session()

    try:
        # Step 1: Crawl
        t0 = time.time()
        raw_articles, feed_stats = crawl_all_feeds(max_age_days=MAX_ARTICLE_AGE_DAYS)
        crawl_time = time.time() - t0

        stats["crawl"]["articles"] = len(raw_articles)
        stats["crawl"]["seconds"] = round(crawl_time, 2)
        stats["feed_stats"] = feed_stats
        logger.info(f"Crawled {len(raw_articles)} articles in {crawl_time:.1f}s\n")

        if not raw_articles:
            stats["status"] = "empty"
            stats["error"] = "No articles crawled"
            _finalize(stats, pipeline_start, db)
            return stats

        # Step 2: Filter
        t0 = time.time()
        ai_articles = filter_articles(raw_articles)
        filter_time = time.time() - t0

        stats["filter"]["input"] = len(raw_articles)
        stats["filter"]["output"] = len(ai_articles)
        stats["filter"]["pass_rate"] = (
            round(len(ai_articles) / len(raw_articles), 4) if raw_articles else 0.0
        )
        stats["filter"]["seconds"] = round(filter_time, 2)
        logger.info(f"Kept {len(ai_articles)} AI articles in {filter_time:.1f}s\n")

        if not ai_articles:
            stats["status"] = "empty"
            stats["error"] = "No AI articles found after filtering"
            _finalize(stats, pipeline_start, db)
            return stats

        # Step 3: Embed + Index
        t0 = time.time()

        if db is not None:
            n_stored = embed_and_store_articles(ai_articles, db)
            stats["index"]["db_inserted"] = n_stored
            logger.info(f"Stored {n_stored} articles in PostgreSQL")

        build_and_save_index(ai_articles)
        index_time = time.time() - t0

        stats["index"]["vectors"] = len(ai_articles)
        stats["index"]["seconds"] = round(index_time, 2)
        stats["index"]["avg_embed_seconds"] = (
            round(index_time / len(ai_articles), 4) if ai_articles else 0.0
        )
        logger.info(f"Indexed {len(ai_articles)} articles in {index_time:.1f}s\n")

        source_counts = Counter(a["source"] for a in ai_articles)
        total = len(ai_articles)
        stats["source_distribution"] = [
            {"source": src, "count": cnt, "percentage": round(cnt / total * 100, 1)}
            for src, cnt in source_counts.most_common()
        ]

        stats["status"] = "success"

    except Exception as e:
        stats["status"] = "failed"
        stats["error"] = str(e)
        logger.error(f"Pipeline failed: {e}")

    _finalize(stats, pipeline_start, db)
    return stats


def _finalize(stats: dict, pipeline_start: float, db=None) -> None:
    """Finalize timing, persist stats to JSON and (optionally) PostgreSQL."""
    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    stats["total_seconds"] = round(time.time() - pipeline_start, 2)

    _save_stats_json(stats)

    if db is not None:
        try:
            _save_pipeline_run(db, stats)
        except Exception as e:
            logger.warning(f"Failed to save pipeline run to DB: {e}")
        finally:
            db.close()


def _save_stats_json(stats: dict) -> None:
    """Persist stats to the legacy JSON file."""
    PIPELINE_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PIPELINE_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)
    logger.info(f"Pipeline stats saved to {PIPELINE_STATS_PATH}")


def load_pipeline_stats() -> dict | None:
    """Load the most recent pipeline stats from disk."""
    if not PIPELINE_STATS_PATH.exists():
        return None
    with open(PIPELINE_STATS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# CLI entry point

if __name__ == "__main__":
    stats = run_pipeline()
    print(f"\nPipeline finished: {stats['status']}")
    print(f"  Crawled:  {stats['crawl']['articles']} articles in {stats['crawl']['seconds']}s")
    print(f"  Filtered: {stats['filter']['output']}/{stats['filter']['input']} "
          f"({stats['filter']['pass_rate']:.0%} pass rate)")
    print(f"  Indexed:  {stats['index']['vectors']} vectors in {stats['index']['seconds']}s")
    if stats['index'].get('db_inserted') is not None:
        print(f"  DB:       {stats['index']['db_inserted']} articles stored in PostgreSQL")
    print(f"  Total:    {stats['total_seconds']}s")
