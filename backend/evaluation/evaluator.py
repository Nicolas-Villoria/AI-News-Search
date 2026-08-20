"""
evaluation/evaluator.py — Search quality evaluation framework.

Computes MRR (Mean Reciprocal Rank) and Precision@K for the search
engine using a hand-curated golden test set.  Also runs an ablation
study comparing the full composite ranker against each individual
signal (semantic-only, time-only, keyword-only).
"""

import argparse
import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from engine.ranker import search_db
from config.settings import RANKING_WEIGHTS
from utils.helpers import get_logger
from filter.ai_filter import filter_articles, compute_keyword_score

logger = get_logger(__name__)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
FILTER_GOLDEN_SET_PATH = Path(__file__).parent / "filter_golden_set.json"

ABLATION_CONFIGS = {
    "composite": RANKING_WEIGHTS,
    "semantic_only": {"semantic": 1.0, "time_decay": 0.0, "keyword": 0.0},
    "time_only": {"semantic": 0.0, "time_decay": 1.0, "keyword": 0.0},
    "keyword_only": {"semantic": 0.0, "time_decay": 0.0, "keyword": 1.0},
}


def load_golden_set() -> list[dict]:
    with open(GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_filter_golden_set() -> list[dict]:
    with open(FILTER_GOLDEN_SET_PATH, "r", encoding="utf-8") as f:
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
    db: Session,
    model: SentenceTransformer,
    weights: dict | None = None,
    top_k: int = 10,
) -> dict:
    """Run one query and return per-query metrics."""
    results = search_db(
        query=query,
        db=db,
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
    db: Session,
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
            db=db,
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
    db: Session,
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
            db=db,
            model=model,
            weights=weights,
            top_k=top_k,
        )
        logger.info(
            f"  {name}: MRR={results[name]['mean_mrr']:.3f}  "
            f"P@5={results[name]['mean_precision_at_5']:.3f}"
        )

    return results


def _compute_binary_metrics(tp: int, fp: int, tn: int, fn: int) -> dict:
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_ai_filter(
    threshold: float = 0.1,
    use_llm_fallback: bool = False,
) -> dict:
    """Evaluate AI theme filtering against a labeled golden set."""
    golden_set = load_filter_golden_set()
    per_example = []

    tp = fp = tn = fn = 0
    total_llm_calls = 0
    total_llm_kept = 0
    total_llm_capped = 0

    for item in golden_set:
        article = {
            "title": item.get("title", ""),
            "text": item.get("text", ""),
        }
        expected = bool(item.get("expected_is_ai_related", False))
        keyword_score = round(compute_keyword_score(f"{article['title']} {article['text']}"), 4)

        if use_llm_fallback:
            kept, stats = filter_articles([article], threshold=threshold, return_stats=True)
            predicted = len(kept) == 1
            total_llm_calls += int(stats.get("llm_fallback_called", 0))
            total_llm_kept += int(stats.get("llm_fallback_kept", 0))
            total_llm_capped += int(stats.get("llm_fallback_skipped_capped", 0))
        else:
            predicted = keyword_score >= threshold

        if expected and predicted:
            tp += 1
        elif not expected and predicted:
            fp += 1
        elif not expected and not predicted:
            tn += 1
        else:
            fn += 1

        per_example.append(
            {
                "id": item.get("id"),
                "category": item.get("category", ""),
                "expected_is_ai_related": expected,
                "predicted_is_ai_related": predicted,
                "keyword_score": keyword_score,
                "title": item.get("title", ""),
            }
        )

    metrics = _compute_binary_metrics(tp, fp, tn, fn)
    return {
        "threshold": threshold,
        "use_llm_fallback": use_llm_fallback,
        "num_examples": len(golden_set),
        "confusion_matrix": {"tp": tp, "fp": fp, "tn": tn, "fn": fn},
        "metrics": metrics,
        "llm_fallback_stats": {
            "called": total_llm_calls,
            "kept": total_llm_kept,
            "skipped_capped": total_llm_capped,
        },
        "per_example": per_example,
    }


# CLI entry point

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run search and filter evaluations.")
    parser.add_argument(
        "--mode",
        choices=["search", "filter", "all"],
        default="all",
        help="Evaluation mode to run.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.1,
        help="Keyword threshold for filter evaluation.",
    )
    parser.add_argument(
        "--use-llm-fallback",
        action="store_true",
        help="Use full filter path with LLM fallback in filter evaluation.",
    )
    args = parser.parse_args()

    from db.database import SessionLocal
    from indexer.build_index import load_embedding_model

    if args.mode in {"search", "all"}:
        db = SessionLocal()
        model = load_embedding_model()
        print("Running search ablation study...\n")
        ablation = run_ablation(db, model)
        print(f"\n{'='*60}")
        print(f"  {'Config':<20s} {'MRR':>8s} {'P@5':>8s}")
        print(f"{'='*60}")
        for name, result in ablation.items():
            print(f"  {name:<20s} {result['mean_mrr']:>8.3f} {result['mean_precision_at_5']:>8.3f}")
        print(f"{'='*60}")
        db.close()

    if args.mode in {"filter", "all"}:
        print("\nRunning AI theme filter evaluation...\n")
        filter_eval = evaluate_ai_filter(
            threshold=args.threshold,
            use_llm_fallback=args.use_llm_fallback,
        )
        cm = filter_eval["confusion_matrix"]
        m = filter_eval["metrics"]
        print(f"  Examples:   {filter_eval['num_examples']}")
        print(f"  Threshold:  {filter_eval['threshold']}")
        print(f"  LLM fallback enabled: {filter_eval['use_llm_fallback']}")
        print(f"  TP/FP/TN/FN: {cm['tp']}/{cm['fp']}/{cm['tn']}/{cm['fn']}")
        print(
            f"  Accuracy: {m['accuracy']:.3f}  Precision: {m['precision']:.3f}  "
            f"Recall: {m['recall']:.3f}  F1: {m['f1']:.3f}"
        )
        if filter_eval["use_llm_fallback"]:
            llm = filter_eval["llm_fallback_stats"]
            print(
                f"  LLM fallback calls/kept/capped: "
                f"{llm['called']}/{llm['kept']}/{llm['skipped_capped']}"
            )
