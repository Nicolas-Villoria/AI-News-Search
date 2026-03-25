"""
indexer/build_index.py — Sentence embedding + pgvector storage.

Embeds article text using SentenceTransformers (all-MiniLM-L6-v2)
and stores the results in PostgreSQL via pgvector.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL_NAME
from utils.helpers import get_logger

logger = get_logger(__name__)


def _normalize_l2(arr: np.ndarray) -> None:
    """In-place L2 normalisation (rows)"""
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1
    arr /= norms


# ── Model loading (singleton) ────────────────────────────────────────

_model_cache: SentenceTransformer | None = None


def load_embedding_model() -> SentenceTransformer:
    """Load the sentence-transformer embedding model (cached after first call)."""
    global _model_cache
    if _model_cache is not None:
        return _model_cache
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    _model_cache = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded successfully")
    return _model_cache


# ── Embedding ────────────────────────────────────────────────────────

def embed_articles(articles: list[dict], model: SentenceTransformer) -> np.ndarray:
    """Encode articles into dense vector embeddings.

    Each article is represented as "{title}. {first 500 chars of body}"
    to stay within MiniLM's 256-token limit while capturing the lead.
    """
    texts = [
        f"{a['title']}. {a.get('text', '')[:500]}" for a in articles
    ]

    logger.info(f"Embedding {len(texts)} articles …")
    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True,
    )

    logger.info(f"Embeddings shape: {embeddings.shape}")
    return embeddings.astype(np.float32)


# ── PostgreSQL + pgvector storage ────────────────────────────────────

def embed_and_store_articles(articles: list[dict], db) -> int:
    """Compute embeddings and insert articles into PostgreSQL with pgvector.

    Skips articles whose URL already exists in the database.
    Returns the number of newly inserted rows.
    """
    from sqlalchemy import select
    from dateutil import parser as dateutil_parser
    from db.models import Article

    model = load_embedding_model()
    embeddings = embed_articles(articles, model)
    _normalize_l2(embeddings)

    existing_urls = set(
        row[0] for row in db.execute(select(Article.url)).all()
    )

    inserted = 0
    for article, emb in zip(articles, embeddings):
        url = article.get("link", article.get("url", ""))
        if url in existing_urls:
            continue

        published = None
        if article.get("published"):
            try:
                published = dateutil_parser.parse(article["published"])
            except Exception:
                pass

        db.add(Article(
            title=article["title"],
            url=url,
            source=article.get("source"),
            published=published,
            body=article.get("text", ""),
            keyword_score=article.get("keyword_score", 0.0),
            embedding=emb.tolist(),
        ))
        inserted += 1

    db.commit()
    logger.info(f"Stored {inserted} new articles in PostgreSQL ({len(existing_urls)} already existed)")
    return inserted
