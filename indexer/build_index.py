"""
indexer/build_index.py - Sentence embedding + FAISS index builder.

Embeds article text using SentenceTransformers (all-MiniLM-L6-v2),
builds a FAISS inner-product index for semantic search, and persists
everything to disk.

"""

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from config.settings import (
    EMBEDDING_MODEL_NAME,
    EMBEDDING_DIM,
    ARTICLES_PATH,
    FAISS_INDEX_PATH,
    EMBEDDINGS_PATH,
)
from utils.helpers import get_logger, load_articles_json, save_articles_json

logger = get_logger(__name__)


# Model loading 

def load_embedding_model() -> SentenceTransformer:
    """
    Load the sentence-transformer embedding model.
    """
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded successfully")
    return model


# Embedding 

def embed_articles(articles: list[dict], model: SentenceTransformer) -> np.ndarray:
    """
    Encode articles into dense vector embeddings.
    """
    # We embed the title and the first 500 chars of the text
    # Truncate at 500 chars to fit within MiniLM's 256-token limit and focus on the lead
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


# FAISS index 

def build_faiss_index(embeddings: np.ndarray) -> faiss.IndexFlatIP:
    """
    Build a FAISS inner-product index from normalized embeddings.
    """
    # Normalize in-place to make inner product equivalent to cosine similarity
    faiss.normalize_L2(embeddings)

    # IndexFlatIP = exact brute-force inner-product search
    index = faiss.IndexFlatIP(EMBEDDING_DIM)
    index.add(embeddings)

    logger.info(f"FAISS index built: {index.ntotal} vectors, dim={EMBEDDING_DIM}")
    return index


# Persistence 

def save_index(
    index: faiss.IndexFlatIP,
    embeddings: np.ndarray) -> None:
    """
    Save the FAISS index and raw embeddings.

    Two files are written:
        data/faiss_index.bin  — FAISS binary index (for fast search)
        data/embeddings.npy   — raw numpy embeddings (for reloading)
    """
    faiss.write_index(index, str(FAISS_INDEX_PATH))
    np.save(str(EMBEDDINGS_PATH), embeddings)

    logger.info(f"Index saved  to {FAISS_INDEX_PATH}")
    logger.info(f"Embeds saved to {EMBEDDINGS_PATH}")


def load_index() -> tuple[faiss.IndexFlatIP, np.ndarray, list[dict]]:
    """
    Load a previously saved FAISS index, embeddings, and articles.
    """
    for path, label in [
        (FAISS_INDEX_PATH, "FAISS index"),
        (EMBEDDINGS_PATH, "Embeddings"),
        (ARTICLES_PATH, "Articles"),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"{label} not found at {path}. "
                "Run `python -m indexer.build_index` first."
            )

    index = faiss.read_index(str(FAISS_INDEX_PATH))
    embeddings = np.load(str(EMBEDDINGS_PATH))
    articles = load_articles_json(ARTICLES_PATH)

    logger.info(
        f"Loaded index ({index.ntotal} vectors), "
        f"embeddings {embeddings.shape}, "
        f"{len(articles)} articles"
    )
    return index, embeddings, articles


# High-level entry point 

def build_and_save_index(articles: list[dict]) -> tuple[faiss.IndexFlatIP, np.ndarray]:
    """
    End-to-end: embed articles, build FAISS index and save everything.
    """
    model = load_embedding_model()
    embeddings = embed_articles(articles, model)
    index = build_faiss_index(embeddings)
    save_index(index, embeddings)
    save_articles_json(articles, ARTICLES_PATH)
    return index, embeddings


# CLI entry point 

if __name__ == "__main__":
    """Load filtered articles from disk, build index, save, print stats."""
    articles = load_articles_json(ARTICLES_PATH)
    if not articles:
        logger.warning(f"No articles at {ARTICLES_PATH}. Run crawler + filter first.")
        raise SystemExit(1)

    logger.info(f"Loaded {len(articles)} articles")
    index, embeddings = build_and_save_index(articles)

    # Quick sanity check: search for "AI" and show top 3
    model = load_embedding_model()
    query_vec = model.encode(["latest artificial intelligence news"], convert_to_numpy=True).astype(np.float32)
    faiss.normalize_L2(query_vec)
    scores, indices = index.search(query_vec, 3)

    print("\n── Sanity check: top 3 for 'latest artificial intelligence news' ────────")
    for rank, (score, idx) in enumerate(zip(scores[0], indices[0]), 1):
        a = articles[idx]
        print(f"  #{rank}  sim={score:.4f}  {a['title']}")
        print(f"       {a['source']}")
    print()
