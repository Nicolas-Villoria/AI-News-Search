"""
engine/summarizer.py — AI-powered article summarization.

Uses a Hugging Face summarization pipeline (DistilBART) to generate
concise summaries of news articles. Summaries are computed on-demand
and cached on the article dict so they're only generated once.

Performance notes:
    - DistilBART takes ~3–5 s per article on CPU.
    - For 10 articles that's ~40 s. Acceptable for an MVP.
    - GPU or a lighter model (t5-small) speeds this up significantly.
    - The UI only summarises top-ranked articles, not all 100+.

Usage:
    python -m engine.summarizer              # standalone test
    from engine.summarizer import load_summarizer, summarize_articles
"""

from transformers import pipeline as hf_pipeline
from tqdm import tqdm

from config.settings import (
    SUMMARIZER_MODEL_NAME,
    SUMMARY_MAX_LENGTH,
    SUMMARY_MIN_LENGTH,
    ARTICLES_PATH,
)
from utils.helpers import get_logger, load_articles_json

logger = get_logger(__name__)

# DistilBART's maximum input is 1024 tokens (~3000 chars).
# We truncate to stay safely within that window.
MAX_INPUT_CHARS = 2500


# ── Model loading ────────────────────────────────────────────────

def load_summarizer():
    """Load the Hugging Face summarization pipeline.

    First call downloads the model (~1.2 GB for DistilBART).
    Subsequent calls use the local cache (~/.cache/huggingface/).

    Returns:
        A transformers.Pipeline configured for summarization.
    """
    logger.info(f"Loading summarization model: {SUMMARIZER_MODEL_NAME}")
    summarizer = hf_pipeline(
        "summarization",
        model=SUMMARIZER_MODEL_NAME,
        tokenizer=SUMMARIZER_MODEL_NAME,
    )
    logger.info("Summarizer loaded ✓")
    return summarizer


# ── Single-article summarization ─────────────────────────────────

def summarize_text(text: str, summarizer) -> str:
    """Generate a concise summary of a single article's text.

    Handles edge cases:
        - Empty / very short text → returns fallback message
        - Model errors → returns fallback instead of crashing
        - Input truncated to MAX_INPUT_CHARS to respect model limits

    Args:
        text:        The article body text.
        summarizer:  Loaded HF summarization pipeline.

    Returns:
        Summary string, or a fallback message on failure.
    """
    if not text or len(text.strip()) < 100:
        return "Summary unavailable — article text too short."

    try:
        # Truncate to stay within DistilBART's 1024-token window
        truncated = text[:MAX_INPUT_CHARS]

        result = summarizer(
            truncated,
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            do_sample=False,  # Greedy decoding — deterministic output
        )

        return result[0]["summary_text"].strip()

    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        return "Summary unavailable."


# ── Batch summarization ──────────────────────────────────────────

def summarize_articles(
    articles: list[dict],
    summarizer,
    max_articles: int = 10,
) -> list[dict]:
    """Add AI-generated summaries to the top N articles.

    Only summarises articles that don't already have a summary,
    so re-running is safe and won't waste compute.

    Args:
        articles:     List of article dicts (should be pre-ranked).
        summarizer:   Loaded HF summarization pipeline.
        max_articles: Cap on how many articles to summarise (CPU is slow).

    Returns:
        The same list with a 'summary' field added to each article.
    """
    to_summarise = articles[:max_articles]

    logger.info(f"Summarising {len(to_summarise)} articles …")

    for article in tqdm(to_summarise, desc="Summarising"):
        # Skip if already summarised (idempotent)
        if article.get("summary") and article["summary"] != "Summary unavailable.":
            continue

        article["summary"] = summarize_text(
            article.get("text", ""), summarizer
        )

    # Mark remaining articles as unsummarised
    for article in articles[max_articles:]:
        if "summary" not in article:
            article["summary"] = ""

    logger.info("Summarisation complete ✓")
    return articles


# ── CLI entry point ──────────────────────────────────────────────

if __name__ == "__main__":
    """Load articles, summarise the top 5, print results."""

    articles = load_articles_json(ARTICLES_PATH)
    if not articles:
        logger.warning(f"No articles at {ARTICLES_PATH}. Run the pipeline first.")
        raise SystemExit(1)

    logger.info(f"Loaded {len(articles)} articles")
    summarizer = load_summarizer()

    # Only summarise 5 for this quick test
    summarized = summarize_articles(articles[:5], summarizer, max_articles=5)

    print("\n── Summaries ───────────────────────────────────────")
    for a in summarized:
        print(f"\n  📰 {a['title']}")
        print(f"     {a['source']}")
        print(f"     Summary: {a.get('summary', 'N/A')}")
    print()
