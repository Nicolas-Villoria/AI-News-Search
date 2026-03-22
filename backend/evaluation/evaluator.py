"""
evaluation/evaluator.py — Search quality evaluation framework.

Computes MRR (Mean Reciprocal Rank) and Precision@K for the search
engine using a hand-curated golden test set.  Also runs an ablation
study comparing the full composite ranker against each individual
signal (semantic-only, time-only, keyword-only).
"""

import json
from pathlib import Path

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from engine.ranker import search
from config.settings import RANKING_WEIGHTS
from utils.helpers import get_logger

logger = get_logger(__name__)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"

ABLATION_CONFIGS = {
    "composite": RANKING_WEIGHTS,
    "semantic_only": {"semantic": 1.0, "time_decay": 0.0, "keyword": 0.0},
    "time_only": {"semantic": 0.0, "time_decay": 1.0, "keyword": 0.0},
    "keyword_only": {"semantic": 0.0, "time_decay": 0.0, "keyword": 1.0},
}


def load_golden_set() -> list[dict]:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _is_relevant(article: dict, keywords: list[str]) -> bool:
    """Check if an article matches any of the relevance keywords."""
    text = f"{article.get('title', '')} {article.get('text', '')}".lower()
    return any(kw.lower() in text for kw in keywords)


def compute_mrr(ranked_results: list[dict], relevant_keywords: list[str]) -> float:
    """Mean Reciprocal Rank: 1/rank of the first relevant result.

    Returns 0 if no relevant result is found in the list.
    """
    for rank, article in enumerate(ranked_results, 1):
        if _is_relevant(article, relevant_keywords):
            return 1.0 / rank
    return 0.0


def compute_precision_at_k(
    ranked_results: list[dict],
    relevant_keywords: list[str],
    k: int = 5,
) -> float:
    """Precision@K: fraction of top-K results that are relevant."""
    top_k = ranked_results[:k]
    if not top_k:
        return 0.0
    relevant_count = sum(1 for a in top_k if _is_relevant(a, relevant_keywords))
    return relevant_count / k


def evaluate_single_query(
    query: str,
    relevant_keywords: list[str],
    index: faiss.IndexFlatIP,
    articles: list[dict],
    model: SentenceTransformer,
    weights: dict,
    top_k: int = 10,
) -> dict:
    """Run one query and return per-query metrics."""
    results = search(
        query=query,
        index=index,
        articles=articles,
        model=model,
        top_k=top_k,
        weights=weights,
    )

    mrr = compute_mrr(results, relevant_keywords)
    p_at_5 = compute_precision_at_k(results, relevant_keywords, k=5)

    relevance_flags = [_is_relevant(a, relevant_keywords) for a in results[:5]]

    return {
        "query": query,
        "mrr": round(mrr, 4),
        "precision_at_5": round(p_at_5, 4),
        "top_5_titles": [a["title"] for a in results[:5]],
        "top_5_relevant": relevance_flags,
        "top_5_scores": [a.get("relevance_score", 0) for a in results[:5]],
    }


def run_evaluation(
    index: faiss.IndexFlatIP,
    articles: list[dict],
    model: SentenceTransformer,
    weights: dict | None = None,
    top_k: int = 10,
) -> dict:
    """Run the full golden-set evaluation with one weight config.

    Returns aggregate metrics + per-query breakdown.
    """
    w = weights or RANKING_WEIGHTS
    golden_set = load_golden_set()

    per_query = []
    for item in golden_set:
        result = evaluate_single_query(
            query=item["query"],
            relevant_keywords=item["relevant_keywords"],
            index=index,
            articles=articles,
            model=model,
            weights=w,
            top_k=top_k,
        )
        result["description"] = item.get("description", "")
        per_query.append(result)

    mrr_scores = [q["mrr"] for q in per_query]
    p5_scores = [q["precision_at_5"] for q in per_query]

    return {
        "mean_mrr": round(float(np.mean(mrr_scores)), 4),
        "mean_precision_at_5": round(float(np.mean(p5_scores)), 4),
        "num_queries": len(per_query),
        "per_query": per_query,
    }


def run_ablation(
    index: faiss.IndexFlatIP,
    articles: list[dict],
    model: SentenceTransformer,
    top_k: int = 10,
) -> dict:
    """Run the golden-set evaluation under all ablation configs.

    Returns a dict keyed by config name, each containing aggregate
    metrics and per-query breakdowns.
    """
    results = {}
    for name, weights in ABLATION_CONFIGS.items():
        logger.info(f"Running ablation: {name} (weights={weights})")
        results[name] = run_evaluation(
            index=index,
            articles=articles,
            model=model,
            weights=weights,
            top_k=top_k,
        )
        logger.info(
            f"  {name}: MRR={results[name]['mean_mrr']:.3f}  "
            f"P@5={results[name]['mean_precision_at_5']:.3f}"
        )

    return results


# CLI entry point

if __name__ == "__main__":
    from indexer.build_index import load_index, load_embedding_model

    index, embeddings, articles = load_index()
    model = load_embedding_model()

    print("Running ablation study...\n")
    ablation = run_ablation(index, articles, model)

    print(f"\n{'='*60}")
    print(f"  {'Config':<20s} {'MRR':>8s} {'P@5':>8s}")
    print(f"{'='*60}")
    for name, result in ablation.items():
        print(f"  {name:<20s} {result['mean_mrr']:>8.3f} {result['mean_precision_at_5']:>8.3f}")
    print(f"{'='*60}")
