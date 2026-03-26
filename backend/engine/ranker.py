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
from sqlalchemy import text, select
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


def search_db(
    query: str,
    db: Session,
    model: SentenceTransformer,
    top_k: int = MAX_ARTICLES_DISPLAY,
    weights: dict | None = None,
    cluster_id: int | None = None,
    ) -> list[dict]:
    """Search articles with pgvector cosine similarity + composite ranking.
    
    If query is empty, returns the latest articles ordered by publication date.
    """
    w = weights or RANKING_WEIGHTS
    query = query.strip()
    
    cluster_filter = "AND cluster_id = :cluster_id" if cluster_id is not None else ""
    
    if not query:
        # Fallback for empty query: Just show latest articles
        sql_text = f"""
            SELECT
                id, title, url, source, published, body, keyword_score, cluster_id,
                0.0 AS semantic_score,
                1.0 AS time_score,
                0.0 AS relevance_score
            FROM articles
            WHERE NOT is_duplicate {cluster_filter}
            ORDER BY published DESC NULLS LAST, created_at DESC
            LIMIT :top_k
        """
        params = {"top_k": top_k}
        if cluster_id is not None:
            params["cluster_id"] = cluster_id
    else:
        # Standard semantic search
        query_vec = _encode_query(query, model)
        vec_literal = "[" + ",".join(str(float(x)) for x in query_vec[0]) + "]"

        sql_text = f"""
            WITH scored AS (
                SELECT
                    id, title, url, source, published, body, keyword_score, cluster_id,
                    1 - (embedding <=> :qvec ::vector) AS semantic_score,
                    CASE WHEN published IS NOT NULL
                         THEN pow(2, -EXTRACT(EPOCH FROM (NOW() - published)) / 3600.0 / :half_life)
                         ELSE 0 END AS time_score
                FROM articles
                WHERE embedding IS NOT NULL AND NOT is_duplicate {cluster_filter}
            )
            SELECT *,
                :w_sem * semantic_score
              + :w_time * time_score
              + :w_kw  * COALESCE(keyword_score, 0)
                AS relevance_score
            FROM scored
            ORDER BY relevance_score DESC
            LIMIT :top_k
        """

        params = {
            "qvec": vec_literal,
            "half_life": TIME_DECAY_HALF_LIFE_HOURS,
            "w_sem": w["semantic"],
            "w_time": w["time_decay"],
            "w_kw": w["keyword"],
            "top_k": top_k,
        }
        if cluster_id is not None:
            params["cluster_id"] = cluster_id

    rows = db.execute(text(sql_text), params).fetchall()

    article_ids = [row.id for row in rows]
    entities_by_article = {aid: [] for aid in article_ids}
    cluster_by_article = {row.id: row.cluster_id for row in rows}

    if article_ids:
        from db.models import Entity
        entities = db.execute(
            select(Entity).where(Entity.article_id.in_(article_ids))
        ).scalars().all()
        for e in entities:
            entities_by_article[e.article_id].append({
                "name": e.name,
                "label": e.label,
                "count": e.count,
            })

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
            "cluster_id": cluster_by_article[row.id],
            "entities": entities_by_article[row.id],
        })

    return results
