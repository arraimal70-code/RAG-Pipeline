r"""
src/retrieval/mmr.py — Maximal Marginal Relevance (MMR) Diversity Reranking.

Solves the classic RAG redundancy problem (Carbonell & Goldstein, 1998):
Standard top-K retrieval frequently returns 4 or 5 near-identical chunks from
the same section or repetitive boilerplate.

Maximal Marginal Relevance balances Query Relevance and Context Diversity:
MMR(q, D) = argmax_{d_i in D \ S} [ lambda * Sim(d_i, q) - (1 - lambda) * max_{d_j in S} Sim(d_i, d_j) ]

Where:
- D is the set of all retrieved candidates.
- S is the subset of already selected diverse candidates.
- lambda in [0, 1] controls the exploration/exploitation trade-off:
  - lambda = 1.0: pure similarity (standard retrieval)
  - lambda = 0.5: balanced relevance and diversity
  - lambda = 0.0: maximal diversity
"""

import math
import logging
from typing import List, Dict, Any, Optional

from src.core.models import RetrievalResult, TextChunk
from src.embeddings.embedder import Embedder, get_embedder

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Compute cosine similarity between two numeric vectors."""
    norm1 = math.sqrt(sum(x * x for x in vec1))
    norm2 = math.sqrt(sum(x * x for x in vec2))
    if norm1 < 1e-9 or norm2 < 1e-9:
        return 0.0
    return sum(x * y for x, y in zip(vec1, vec2)) / (norm1 * norm2)


class MaximalMarginalRelevanceReranker:
    """
    Reranks candidates to maximize information diversity while preserving high query relevance.
    """

    def __init__(self, lambda_param: float = 0.65, embedder: Optional[Embedder] = None):
        self.lambda_param = lambda_param
        self.embedder = embedder or get_embedder()

    def rerank(
        self,
        query: str,
        candidates: List[RetrievalResult],
        top_k: int = 5,
        lambda_param: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        Apply MMR to select a non-redundant subset of candidate chunks.
        """
        if not candidates or len(candidates) <= 1:
            return candidates[:top_k]

        lam = lambda_param if lambda_param is not None else self.lambda_param
        query_vec = self.embedder.embed_query(query)

        # Precompute candidate embeddings
        candidate_texts = [c.chunk.content for c in candidates]
        candidate_embeddings = self.embedder.embed(candidate_texts)

        selected_indices: List[int] = []
        remaining_indices = list(range(len(candidates)))

        # Step 1: Select the candidate with highest query similarity
        sims_to_query = [
            cosine_similarity(query_vec, candidate_embeddings[i])
            for i in remaining_indices
        ]
        best_first = int(max(range(len(sims_to_query)), key=lambda idx: sims_to_query[idx]))
        selected_indices.append(remaining_indices.pop(best_first))

        # Step 2: Iteratively select candidates maximizing MMR formula
        while len(selected_indices) < min(top_k, len(candidates)) and remaining_indices:
            best_mmr_score = -float("inf")
            best_cand_idx = -1

            for rem_idx in remaining_indices:
                cand_vec = candidate_embeddings[rem_idx]
                sim_to_q = cosine_similarity(query_vec, cand_vec)

                # Find max similarity to any already selected candidate
                max_sim_to_selected = max(
                    cosine_similarity(cand_vec, candidate_embeddings[sel_idx])
                    for sel_idx in selected_indices
                )

                mmr_score = lam * sim_to_q - (1.0 - lam) * max_sim_to_selected
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_cand_idx = rem_idx

            if best_cand_idx != -1:
                selected_indices.append(best_cand_idx)
                remaining_indices.remove(best_cand_idx)
            else:
                break

        # Construct final ordered results
        diverse_results = []
        for rank, idx in enumerate(selected_indices, 1):
            original = candidates[idx]
            diverse_results.append(RetrievalResult(
                chunk=original.chunk,
                score=original.score,
                retrieval_method=f"{original.retrieval_method}+mmr",
                rank=rank,
            ))

        logger.info(f"MMR Reranker: Filtered {len(candidates)} candidates down to {len(diverse_results)} diverse chunks (lambda={lam})")
        return diverse_results
