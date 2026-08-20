"""
filter/ai_filter.py — Keyword-based AI topic filter.

Determines whether an article is AI-related by checking how many
curated AI keywords appear in its title + body text. Also computes
a keyword_score (0-1) that feeds into the downstream ranker.

"""
import os

from config.settings import (
    AI_KEYWORDS,
    ARTICLES_PATH,
    LLM_FALLBACK_MAX_CALLS,
    LLM_FALLBACK_MIN_CONFIDENCE,
)
from utils.helpers import get_logger, load_articles_json, save_articles_json
from utils.open_router import OpenRouterJudgeAgent


logger = get_logger(__name__)


def compute_keyword_score(text: str) -> float:
    """Score how AI-dense an article is based on keyword matches.

    Counts how many distinct AI keywords appear in the text
    (case-insensitive) and returns a ratio: matched / total keywords.

    """
    text_lower = text.lower()
    # Count how many keywords appear in the text
    matches = sum(1 for kw in AI_KEYWORDS if kw in text_lower)
    # Return score as ratio of matches to total keywords (0 to 1)
    return matches / len(AI_KEYWORDS)


def ai_filter(
    article: str,
    judge: OpenRouterJudgeAgent | None = None,
) -> tuple[bool, float]:
    """Fallback filter for articles that don't meet the keyword score threshold.

    It uses an LLM as a judge from OpenRouter to determine if the article is AI-related based on its title and text.
    """
    llm_judge = judge or OpenRouterJudgeAgent(api_key=os.environ.get("OPENROUTER_API_KEY"))
    result = llm_judge.judge(article)

    logger.debug(
        f"LLM judge result: label={result.is_ai_related}, "
        f"confidence={result.confidence:.2f}, reason='{result.reason}'"
    )

    accepted = result.is_ai_related and result.confidence >= LLM_FALLBACK_MIN_CONFIDENCE
    return accepted, result.confidence


def _keep_article(article: dict, score: float, kept: list[dict]) -> None:
    """Attach keyword score and append to kept list."""
    article["keyword_score"] = round(score, 4)
    kept.append(article)


def filter_articles(
    articles: list[dict],
    threshold: float = 0.2,
    *,
    return_stats: bool = False,
) -> list[dict] | tuple[list[dict], dict]:
    """
    Filter a list of articles to only AI-related ones.

    Each passing article gets a 'keyword_score' field attached,
    which the ranker will use later as one of three ranking signals.
    """
    kept: list[dict] = []
    llm_fallback_calls = 0
    llm_fallback_kept = 0
    llm_fallback_skipped_capped = 0
    llm_judge: OpenRouterJudgeAgent | None = None

    for article in articles:
        combined = f"{article.get('title', '')} {article.get('text', '')}"
        score = compute_keyword_score(combined)

        if score >= threshold:
            _keep_article(article, score, kept)
            continue

        if llm_fallback_calls >= LLM_FALLBACK_MAX_CALLS:
            llm_fallback_skipped_capped += 1
            logger.debug(
                "Skipping LLM fallback for '%s' due to call cap (%s).",
                article.get("title", "N/A"),
                LLM_FALLBACK_MAX_CALLS,
            )
            continue

        if llm_judge is None:
            llm_judge = OpenRouterJudgeAgent(api_key=os.environ.get("OPENROUTER_API_KEY"))

        llm_fallback_calls += 1
        accepted_by_llm, confidence = ai_filter(combined, judge=llm_judge)
        if accepted_by_llm:
            llm_fallback_kept += 1
            _keep_article(article, score, kept)
        else:
            logger.debug(
                "Article '%s' filtered out (score=%.4f, llm_confidence=%.2f)",
                article.get("title", "N/A"),
                score,
                confidence,
            )


    logger.info(
        f"AI filter: {len(kept)}/{len(articles)} articles passed "
        f"(threshold={threshold})"
    )
    stats = {
        "llm_fallback_called": llm_fallback_calls,
        "llm_fallback_kept": llm_fallback_kept,
        "llm_fallback_skipped_capped": llm_fallback_skipped_capped,
    }

    if return_stats:
        return kept, stats
    return kept


# CLI entry point 

if __name__ == "__main__":
    """Load crawled articles, filter to AI-only, save back, print stats."""

    articles = load_articles_json(ARTICLES_PATH)
    if not articles:
        logger.warning(f"No articles found at {ARTICLES_PATH}. Run the crawler first.")
        raise SystemExit(1)

    logger.info(f"Loaded {len(articles)} articles from {ARTICLES_PATH}")

    filtered = filter_articles(articles)

    if filtered:
        save_articles_json(filtered, ARTICLES_PATH)
        logger.info(f"Saved {len(filtered)} AI articles to {ARTICLES_PATH}")
    else:
        logger.warning("No AI-related articles found after filtering.")
