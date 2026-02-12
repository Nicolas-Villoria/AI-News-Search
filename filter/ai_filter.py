"""
filter/ai_filter.py — Keyword-based AI topic filter.

Determines whether an article is AI-related by checking how many
curated AI keywords appear in its title + body text. Also computes
a keyword_score (0-1) that feeds into the downstream ranker.

"""

from config.settings import AI_KEYWORDS, ARTICLES_PATH
from utils.helpers import get_logger, load_articles_json, save_articles_json

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


def is_ai_related(article: dict, threshold: float = 0.02) -> bool:
    """
    Check whether an article is about AI.
    """
    combined = f"{article.get('title', '')} {article.get('text', '')}"
    score = compute_keyword_score(combined)
    # Threshold is tunable. Currently set to 0.02, 
    # meaning an article must match at least 1/52 keywords
    return score >= threshold


def filter_articles(articles: list[dict], threshold: float = 0.02) -> list[dict]:
    """
    Filter a list of articles to only AI-related ones.

    Each passing article gets a 'keyword_score' field attached,
    which the ranker will use later as one of three ranking signals.
    """
    kept = []

    for article in articles:
        combined = f"{article.get('title', '')} {article.get('text', '')}"
        score = compute_keyword_score(combined)

        if score >= threshold:
            article["keyword_score"] = round(score, 4)
            kept.append(article)

    logger.info(
        f"AI filter: {len(kept)}/{len(articles)} articles passed "
        f"(threshold={threshold})"
    )
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
