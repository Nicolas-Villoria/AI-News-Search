"""
pipeline/run_pipeline.py — End-to-end data pipeline orchestrator.

Runs the full ingestion pipeline in order and collects timing /
success metrics for the Pipeline Health dashboard.

Stores articles in PostgreSQL + pgvector and writes a JSON stats
file for the health dashboard.
"""

import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from dateutil import parser as dateutil_parser

from sqlalchemy import select

from db.models import Article, PipelineRun
from crawler.rss_crawler import crawl_all_feeds
from filter.ai_filter import filter_articles
from indexer.build_index import embed_and_store_articles
from engine.topic_engine import cluster_recent_articles
from config.settings import MAX_ARTICLE_AGE_DAYS, MAX_ARTICLE_RETENTION_DAYS
from utils.helpers import get_logger

logger = get_logger(__name__)


def _get_db_session():
    """Try to open a DB session. Returns None if the database is unavailable.

    Also ensures tables + pgvector extension exist (idempotent) so the
    pipeline can run against a fresh database without a prior init step.
    """
    try:
        from db.init_db import init_db
        from db.database import SessionLocal
        init_db()
        db = SessionLocal()
        db.connection()
        return db
    except Exception as e:
        logger.error(f"Database initialization or connection failed: {e}")
        return None


def _get_existing_urls(db) -> set[str]:
    """Return all article URLs currently stored in PostgreSQL."""
    return set(row[0] for row in db.execute(select(Article.url)).all())


def _save_pipeline_run(db, stats: dict) -> None:
    """Write or update the pipeline_runs row in PostgreSQL."""
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


def _garbage_collect(db, retention_days: int = MAX_ARTICLE_RETENTION_DAYS) -> int:
    """Delete articles (and their entities) older than *retention_days* (90).
    Also cleans up orphaned TopicClusters.

    Returns the number of deleted rows.
    """
    from db.models import TopicCluster

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    deleted = (
        db.query(Article)
        .filter(Article.created_at < cutoff)
        .delete(synchronize_session="fetch")
    )
    
    # Clean up empty topic clusters
    db.query(TopicCluster).filter(
        TopicCluster.id.not_in(select(Article.cluster_id).where(Article.cluster_id.is_not(None)))
    ).delete(synchronize_session=False)

    db.commit()
    return deleted


def _finalize(stats: dict, pipeline_start: float, db=None) -> None:
    """Finalize timing, persist stats to JSON and (optionally) PostgreSQL."""
    stats["finished_at"] = datetime.now(timezone.utc).isoformat()
    stats["total_seconds"] = round(time.time() - pipeline_start, 2)

    if db is not None:
        try:
            _save_pipeline_run(db, stats)
        except Exception as e:
            logger.warning(f"Failed to save pipeline run to DB: {e}")

        try:
            _garbage_collect(db)
        except Exception as e:
            logger.warning(f"Garbage collection failed: {e}")

        db.close()


def run_pipeline() -> dict:
    """Execute the full data pipeline: crawl -> filter -> embed -> store.

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
        # Fetch existing URLs so the crawler can skip them
        existing_urls = _get_existing_urls(db) if db is not None else set()

        # Crawl
        t0 = time.time()
        raw_articles, feed_stats = crawl_all_feeds(
            max_age_days=MAX_ARTICLE_AGE_DAYS,
            existing_urls=existing_urls,
        )
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

        # Filter
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

        # Embed and store in PostgreSQL
        t0 = time.time()

        if db is not None:
            n_stored = embed_and_store_articles(ai_articles, db)
            stats["index"]["db_inserted"] = n_stored
            logger.info(f"Stored {n_stored} articles in PostgreSQL")
        else:
            logger.error("No database connection — articles were not persisted")
            raise RuntimeError("Database connection failed during ingestion")

        index_time = time.time() - t0

        stats["index"]["vectors"] = len(ai_articles)
        stats["index"]["seconds"] = round(index_time, 2)
        stats["index"]["avg_embed_seconds"] = (
            round(index_time / len(ai_articles), 4) if ai_articles else 0.0
        )
        logger.info(f"Embedded {len(ai_articles)} articles in {index_time:.1f}s\n")

        # Re-cluster into topics
        if db is not None:
            t0_cluster = time.time()
            cluster_recent_articles(db)
            stats["index"]["cluster_seconds"] = round(time.time() - t0_cluster, 2)

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
