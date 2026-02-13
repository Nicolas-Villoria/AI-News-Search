"""
pipeline/run_pipeline.py — End-to-end data pipeline orchestrator.

Runs the full ingestion pipeline in order:
"""

import time

from crawler.rss_crawler import crawl_all_feeds
from filter.ai_filter import filter_articles
from indexer.build_index import build_and_save_index
from config.settings import ARTICLES_PATH
from utils.helpers import get_logger, save_articles_json

logger = get_logger(__name__)


def run_pipeline() -> list[dict]:
    """Execute the full data pipeline: crawl → filter → embed → index → save.

    Returns:
        List of filtered article dicts (with keyword_score and embeddings saved).
    """
    t0 = time.time()

    #  Step 1: Crawl 

    raw_articles = crawl_all_feeds()
    logger.info(f"Crawled {len(raw_articles)} articles\n")

    if not raw_articles:
        logger.warning("No articles crawled. Aborting pipeline.")
        return []

    #  Step 2: Filter 
    ai_articles = filter_articles(raw_articles)
    logger.info(f"Kept {len(ai_articles)} AI articles\n")

    if not ai_articles:
        logger.warning("No AI articles found after filtering. Aborting.")
        return []

    #  Step 3: Embed + Index
    build_and_save_index(ai_articles)
    return ai_articles


#  CLI entry point 

if __name__ == "__main__":
    run_pipeline()
