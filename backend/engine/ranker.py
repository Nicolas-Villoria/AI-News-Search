"""
engine/ranker.py — Composite ranking engine for AI news articles.

"""

import math
from datetime import datetime, timezone

import numpy as np
import faiss
from dateutil import parser as dateutil_parser
from sentence_transformers import SentenceTransformer

from config.settings import (
    RANKING_WEIGHTS,
    TIME_DECAY_HALF_LIFE_HOURS,
    MAX_ARTICLES_DISPLAY,
    EMBEDDING_MODEL_NAME,
)
from utils.helpers import get_logger, hours_since

logger = get_logger(__name__)


# Time-decay scoring 

def compute_time_decay(published: datetime | None) -> float:
    """
    Score an article's freshness using exponential decay.
    """
    if isinstance(published, str):
        try:
            published = dateutil_parser.parse(published)
        except Exception:
            return 0.0

    age_hours = hours_since(published)
    # score is 2^(-age / half_life), so it halves every half-life hours
    return math.pow(2, -age_hours / TIME_DECAY_HALF_LIFE_HOURS)


# Core search + ranking 

def search(
    query: str,
    index: faiss.IndexFlatIP,
    articles: list[dict],
    model: SentenceTransformer,
    top_k: int = MAX_ARTICLES_DISPLAY,
    weights: dict | None = None,
) -> list[dict]:
    """
    Search articles by query and rank with the composite score.
    """
    w = weights or RANKING_WEIGHTS

    # Embed & normalise the query 
    query_vec = model.encode([query], convert_to_numpy=True).astype(np.float32)
    faiss.normalize_L2(query_vec)

    # FAISS search 
    # Retrieve more candidates than top_k so re-ranking can reshuffle
    n_candidates = min(top_k * 2, index.ntotal)
    scores, indices = index.search(query_vec, n_candidates)

    # Score each candidate 
    results = []
    for sim_score, idx in zip(scores[0], indices[0]):
        if idx < 0 or idx >= len(articles):
            continue  # FAISS can return -1 for padded results

        article = articles[idx].copy()  # Don't mutate the originals

        semantic = float(np.clip(sim_score, 0.0, 1.0))
        time_sc = compute_time_decay(article.get("published"))
        keyword = float(article.get("keyword_score", 0.0))

        # Composite weighted score
        relevance = (
            w["semantic"] * semantic
            + w["time_decay"] * time_sc
            + w["keyword"] * keyword
        )

        article["semantic_score"] = round(semantic, 4)
        article["time_score"] = round(time_sc, 4)
        article["keyword_score"] = round(keyword, 4)
        article["relevance_score"] = round(relevance, 4)

        results.append(article)

    # Sort by composite score and trim 
    results.sort(key=lambda a: a["relevance_score"], reverse=True)
    return results[:top_k]


# CLI entry point 

if __name__ == "__main__":
    """Quick test: load index, run a query, print ranked results."""
    from indexer.build_index import load_index, load_embedding_model

    index, embeddings, articles = load_index()
    model = load_embedding_model()

    test_queries = [
        "latest artificial intelligence news",
        "large language model agents",
        "AI regulation and safety",
    ]

    for query in test_queries:
        print(f"\n{'═' * 60}")
        print(f"  Query: \"{query}\"")
        print(f"{'═' * 60}")

        results = search(query, index, articles, model, top_k=5)

        for rank, r in enumerate(results, 1):
            print(
                f"  #{rank}  relevance={r['relevance_score']:.3f}  "
                f"(sem={r['semantic_score']:.3f}  "
                f"time={r['time_score']:.3f}  "
                f"kw={r['keyword_score']:.3f})"
            )
            print(f"       {r['title']}")
            print(f"       {r['source']}  |  {r['published']}")
        print()
