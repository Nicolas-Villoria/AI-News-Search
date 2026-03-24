"""
engine/ranker.py — Composite ranking engine for AI news articles.

Uses pgvector cosine distance in PostgreSQL for semantic search,
combined with time-decay and keyword-score signals.
"""

import math
from datetime import datetime, timezone

import numpy as np
from dateutil import parser as dateutil_parser
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.orm import Session

from config.settings import (
    RANKING_WEIGHTS,
    TIME_DECAY_HALF_LIFE_HOURS,
    MAX_ARTICLES_DISPLAY,
)
from utils.helpers import get_logger, hours_since

logger = get_logger(__name__)



def _encode_query(query: str, model: SentenceTransformer) -> np.ndarray:
    """Encode and L2-normalise a query string."""
    vec = model.encode([query], convert_to_numpy=True).astype(np.float32)
    norms = np.linalg.norm(vec, axis=1, keepdims=True)
    norms[norms == 0] = 1
    vec /= norms
    return vec


_SEARCH_SQL = text("""
    WITH scored AS (
        SELECT
            id, title, url, source, published, body, keyword_score,
            1 - (embedding <=> :qvec ::vector) AS semantic_score,
            CASE WHEN published IS NOT NULL
                 THEN pow(2, -EXTRACT(EPOCH FROM (NOW() - published)) / 3600.0 / :half_life)
                 ELSE 0 END AS time_score
        FROM articles
        WHERE embedding IS NOT NULL AND NOT is_duplicate
    )
    SELECT *,
        :w_sem * semantic_score
      + :w_time * time_score
      + :w_kw  * COALESCE(keyword_score, 0)
        AS relevance_score
    FROM scored
    ORDER BY relevance_score DESC
    LIMIT :top_k
""")


def search_db(
    query: str,
    db: Session,
    model: SentenceTransformer,
    top_k: int = MAX_ARTICLES_DISPLAY,
    weights: dict | None = None
    ) -> list[dict]:
    """Search articles with pgvector cosine similarity + composite ranking.

    The entire ranking formula runs inside PostgreSQL in a single query.
    """
    w = weights or RANKING_WEIGHTS
    query_vec = _encode_query(query, model)
    vec_literal = "[" + ",".join(str(float(x)) for x in query_vec[0]) + "]"

    rows = db.execute(_SEARCH_SQL, {
        "qvec": vec_literal,
        "half_life": TIME_DECAY_HALF_LIFE_HOURS,
        "w_sem": w["semantic"],
        "w_time": w["time_decay"],
        "w_kw": w["keyword"],
        "top_k": top_k,
    }).fetchall()

    results = []
    for row in rows:
        results.append({
            "id": row.id,
            "title": row.title,
            "link": row.url,
            "source": row.source,
            "published": row.published.isoformat() if row.published else None,
            "text": row.body,
            "semantic_score": round(float(row.semantic_score), 4),
            "time_score": round(float(row.time_score), 4),
            "keyword_score": round(float(row.keyword_score or 0), 4),
            "relevance_score": round(float(row.relevance_score), 4),
        })

    return results
