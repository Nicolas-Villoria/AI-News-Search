"""
engine/summarizer.py — DistilBART article summarization.

Uses a Hugging Face DistilBART model to generate concise abstractive
summaries of news articles.  Summaries are computed on-demand via the
/summarize endpoint.

NOTE: Requires OMP_NUM_THREADS=1 on macOS Apple Silicon to avoid a
segfault caused by libtorch OpenMP threading + uvloop.  This is set
in api/main.py before any torch import.
"""

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from tqdm import tqdm

from config.settings import (
    SUMMARIZER_MODEL_NAME,
    SUMMARY_MAX_LENGTH,
    SUMMARY_MIN_LENGTH,
    ARTICLES_PATH,
)
from utils.helpers import get_logger, load_articles_json

logger = get_logger(__name__)

MAX_INPUT_CHARS = 2500


def load_summarizer() -> dict:
    """Load the DistilBART tokenizer and model."""
    logger.info(f"Loading summarization model: {SUMMARIZER_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(SUMMARIZER_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(SUMMARIZER_MODEL_NAME)
    logger.info("Summarizer loaded successfully")
    return {"tokenizer": tokenizer, "model": model}


def summarize_text(text: str, summarizer: dict) -> str:
    """Generate an abstractive summary using DistilBART.

    Args:
        text:       Full article body text.
        summarizer: Dict with 'tokenizer' and 'model' keys.
        title:      Article title (reserved for future use).
    """
    if not text or len(text.strip()) < 100:
        return "Summary unavailable — article text too short."

    try:
        tokenizer = summarizer["tokenizer"]
        model = summarizer["model"]

        truncated = text[:MAX_INPUT_CHARS]
        inputs = tokenizer(
            truncated,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )

        summary_ids = model.generate(
            inputs["input_ids"],
            max_length=SUMMARY_MAX_LENGTH,
            min_length=SUMMARY_MIN_LENGTH,
            num_beams=4,
            do_sample=False,
            early_stopping=True,
        )

        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary.strip()

    except Exception as e:
        logger.warning(f"Summarization failed: {e}")
        return "Summary unavailable."


def summarize_articles(
    articles: list[dict],
    summarizer: dict,
    max_articles: int = 10,
) -> list[dict]:
    """Add AI-generated summaries to the top N articles.

    Only summarises articles that don't already have a summary,
    so re-running is safe and won't waste compute.
    """
    to_summarise = articles[:max_articles]

    logger.info(f"Summarising {len(to_summarise)} articles ...")

    for article in tqdm(to_summarise, desc="Summarising"):
        if article.get("summary") and article["summary"] != "Summary unavailable.":
            continue

        article["summary"] = summarize_text(
            article.get("text", ""), summarizer
        )

    for article in articles[max_articles:]:
        if "summary" not in article:
            article["summary"] = ""

    logger.info("Summarisation completed successfully")
    return articles


# CLI entry point

if __name__ == "__main__":
    articles = load_articles_json(ARTICLES_PATH)
    if not articles:
        logger.warning(f"No articles at {ARTICLES_PATH}. Run the pipeline first.")
        raise SystemExit(1)

    logger.info(f"Loaded {len(articles)} articles")
    summarizer = load_summarizer()

    summarized = summarize_articles(articles[:5], summarizer, max_articles=5)

    print("\n── Summaries ───────────────────────────────────────")
    for a in summarized:
        print(f"\n  Article: {a['title']}")
        print(f"     Source: {a['source']}")
        print(f"     Summary: {a.get('summary', 'N/A')}")
    print()
