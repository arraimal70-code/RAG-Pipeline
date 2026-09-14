"""
src/retrieval/rrf.py — Reciprocal Rank Fusion (RRF).

RRF combines ranked lists from multiple retrieval methods into a
single ranked list. It is:
- Parameter-free (except k, which has a standard default)
- Robust to score scale differences between retrievers
- Well-documented in IR literature

Reference: Cormack, G.V., Clarke, C.L.A., and Buettcher, S.
"Reciprocal Rank Fusion outperforms Condorcet and individual
Rank Learning Methods." SIGIR Forum, 2009.

FORMULA:
  RRF_score(d) = Σ 1/(k + rank_i(d))
  where the sum is over all retrieval methods i,
  and rank_i(d) is the rank of document d in method i's output.

WHY RRF over weighted score fusion:
- Score scales differ between retrievers (cosine ∈ [0,1], BM25 ∈ [0,∞))
- Normalizing scores introduces arbitrary choices
- RRF only uses rank information, which is more robust
- RRF has been empirically shown to outperform score fusion in many settings

LIMITATIONS:
- Ignores score magnitudes (a document ranked 1st with score 0.99
  gets the same RRF contribution as one ranked 1st with score 0.51)
- The parameter k controls how much weight is given to top-ranked items
  (smaller k = more weight to top items)
- Standard k=60 is a reasonable default but may not be optimal for all cases

PARAMETER SENSITIVITY:
- k=1: Almost exclusively uses top-ranked items
- k=10: Moderate emphasis on top items
- k=60: Standard default, balanced
- k=100: More democratic, lower-ranked items get more weight
"""

import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
) -> list[dict]:
    """
    Combine multiple ranked lists using Reciprocal Rank Fusion.

    Args:
        ranked_lists: List of ranked result lists.
            Each result must have a "chunk_id" key.
            Results should be sorted by relevance (best first).
        k: RRF constant (default 60). Controls top-item emphasis.

    Returns:
        Combined list sorted by RRF score (descending).
        Each item includes "rrf_score" and "rrf_contributions" keys.
    """
    scores: dict[str, float] = defaultdict(float)
    items: dict[str, dict] = {}
    contributions: dict[str, list[float]] = defaultdict(list)

    for list_idx, ranked_list in enumerate(ranked_lists):
        for rank, item in enumerate(ranked_list):
            cid = item["chunk_id"]
            rrf_score = 1.0 / (k + rank + 1)  # rank is 0-indexed
            scores[cid] += rrf_score
            contributions[cid].append(rrf_score)

            if cid not in items:
                items[cid] = item.copy()

    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for cid in sorted_ids:
        item = items[cid].copy()
        item["rrf_score"] = scores[cid]
        item["rrf_contributions"] = contributions[cid]
        item["score"] = scores[cid]  # for compatibility with pipeline
        results.append(item)

    logger.debug(
        f"RRF fusion: {len(ranked_lists)} lists → {len(results)} unique items "
        f"(k={k})"
    )

    return results


def weighted_score_fusion(
    ranked_lists: list[list[dict]],
    weights: list[float],
) -> list[dict]:
    """
    Alternative: weighted score fusion.

    Requires score normalization. Less robust than RRF when
    score scales differ between retrievers.

    Included for comparison in experiments (EXP-03 vs EXP-04).
    """
    if len(ranked_lists) != len(weights):
        raise ValueError("Number of lists must match number of weights")

    scores: dict[str, float] = defaultdict(float)
    items: dict[str, dict] = {}

    for list_idx, (ranked_list, weight) in enumerate(zip(ranked_lists, weights)):
        if not ranked_list:
            continue

        # Normalize scores to [0, 1]
        max_score = max(item.get("score", 0) for item in ranked_list) or 1.0
        min_score = min(item.get("score", 0) for item in ranked_list)
        score_range = max_score - min_score or 1.0

        for item in ranked_list:
            cid = item["chunk_id"]
            normalized = (item.get("score", 0) - min_score) / score_range
            scores[cid] += normalized * weight

            if cid not in items:
                items[cid] = item.copy()

    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [{**items[cid], "score": scores[cid]} for cid in sorted_ids]
