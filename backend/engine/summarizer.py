"""
engine/summarizer.py — AI-powered article summarization.

Uses a Hugging Face summarization pipeline (DistilBART) to generate
concise summaries of news articles. Summaries are computed on-demand
and cached on the article dict so they're only generated once.
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

# DistilBART's maximum input is 1024 tokens (~3000 chars).
# We truncate to stay safely within that window.
MAX_INPUT_CHARS = 2500


# Model loading 

def load_summarizer() -> dict:
    """
    Load the DistilBART tokenizer and model directly.
    """
    logger.info(f"Loading summarization model: {SUMMARIZER_MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(SUMMARIZER_MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(SUMMARIZER_MODEL_NAME)
    logger.info("Summarizer loaded successfully")
    return {"tokenizer": tokenizer, "model": model}


# Single-article summarization 

def summarize_text(text: str, summarizer: dict) -> str:
    """Generate a concise summary of a single article's text.

    Uses DistilBART's encoder-decoder architecture directly:
        1. Tokenize input text (truncated to model's max length)
        2. Generate summary tokens with beam search
        3. Decode back to a string
    """
    if not text or len(text.strip()) < 100:
        return "Summary unavailable — article text too short."

    try:
        tokenizer = summarizer["tokenizer"]
        model = summarizer["model"]

        # Truncate then tokenize, let the tokenizer handle final truncation
        truncated = text[:MAX_INPUT_CHARS]
        inputs = tokenizer(
            truncated,
            return_tensors="pt",
            max_length=1024,
            truncation=True,
        )

        # Generate with greedy decoding (do_sample=False) for determinism
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


# Batch summarization 

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

    logger.info("Summarisation completed successfully")
    return articles


# CLI entry point 

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
        print(f"\n  Article: {a['title']}")
        print(f"     Source: {a['source']}")
        print(f"     Summary: {a.get('summary', 'N/A')}")
    print()
