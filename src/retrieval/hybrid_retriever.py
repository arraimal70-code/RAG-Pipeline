"""
src/retrieval/hybrid_retriever.py — Hybrid retrieval pipeline with adaptive policy support.

Pipeline:
1. Accept RetrievalPolicy (from query analysis)
2. Dense retrieval (semantic similarity) — adjusted by policy
3. BM25 retrieval (lexical matching) — adjusted by policy
4. Weighted fusion (using policy weights) or RRF
5. Reranking (cross-encoder for precision)
6. Return top-K with full metadata

This is the core retrieval system. Each stage is independently
configurable and measurable for ablation studies.

CRITICAL: This retriever NOW uses RetrievalPolicy to adapt behavior
based on query type. Different query types produce different retrieval
strategies.
"""

import logging
import time
from typing import Optional
from collections import defaultdict

from src.core.config import config
from src.core.models import (
    RetrievalResult, RetrievalOutput, TextChunk, QueryType,
)
from src.indexing.vector_store import VectorIndex
from src.indexing.bm25_index import BM25Index
from src.embeddings.embedder import get_embedder
from src.adaptive.policy import RetrievalPolicy

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval combining dense + BM25 + reranking.

    CRITICAL FEATURE: Supports adaptive retrieval via RetrievalPolicy.
    The policy determines:
    - Dense vs lexical weight balance
    - Number of candidates to retrieve
    - Whether to expand retrieval for ambiguous queries
    - Reranking configuration

    The pipeline is fully configurable via RetrievalConfig for fixed modes,
    or via RetrievalPolicy for adaptive modes.
    """

    def __init__(self):
        self.vector_index = VectorIndex()
        self.bm25_index = BM25Index()
        self.embedder = get_embedder()
        self.cfg = config.retrieval
        self._reranker = None

    def retrieve(
        self,
        query: str,
        policy: Optional[RetrievalPolicy] = None,
    ) -> RetrievalOutput:
        """
        Full retrieval pipeline with optional adaptive policy.

        Args:
            query: The search query
            policy: Optional RetrievalPolicy for adaptive behavior.
                   If None, uses fixed config values.

        Returns:
            RetrievalOutput with ranked candidates and timing info.
        """
        start_time = time.time()
        method_details = {}

        # Determine retrieval parameters
        if policy:
            # Adaptive mode — use policy parameters
            dense_top_k = policy.dense_top_k
            bm25_top_k = policy.lexical_top_k
            dense_weight = policy.dense_weight
            bm25_weight = policy.lexical_weight
            fusion_method = "weighted"  # Use weighted fusion with policy weights
            rerank_enabled = policy.rerank_enabled
            rerank_top_k = policy.rerank_top_k
            method_details["adaptive"] = policy.to_dict()
            logger.info(f"Using adaptive policy: {policy.query_type.value}")
        else:
            # Fixed mode — use config values
            dense_top_k = self.cfg.dense_top_k
            bm25_top_k = self.cfg.bm25_top_k
            dense_weight = self.cfg.dense_weight
            bm25_weight = self.cfg.bm25_weight
            fusion_method = self.cfg.fusion_method
            rerank_enabled = self.cfg.rerank_enabled
            rerank_top_k = self.cfg.rerank_top_k
            method_details["adaptive"] = {"mode": "fixed"}

        # Stage 1: Dense retrieval
        dense_results = self._dense_retrieve(query, top_k=dense_top_k)
        method_details["dense"] = {"candidates": len(dense_results), "top_k": dense_top_k}

        # Stage 2: BM25 retrieval
        bm25_results = self._bm25_retrieve(query, top_k=bm25_top_k)
        method_details["bm25"] = {"candidates": len(bm25_results), "top_k": bm25_top_k}

        # Stage 3: Fusion
        if fusion_method == "rrf":
            fused = self._reciprocal_rank_fusion(dense_results, bm25_results)
        elif fusion_method == "weighted":
            fused = self._weighted_fusion(dense_results, bm25_results, dense_weight, bm25_weight)
        else:
            fused = self._interleave_fusion(dense_results, bm25_results)

        method_details["fusion"] = {
            "method": fusion_method,
            "dense_weight": dense_weight,
            "bm25_weight": bm25_weight,
            "candidates_after_fusion": len(fused),
        }

        # Truncate to post-fusion top-K
        post_fusion_top_k = policy.post_fusion_top_k if policy else self.cfg.post_fusion_top_k
        fused = fused[:post_fusion_top_k]

        # Stage 4: Reranking
        if rerank_enabled and fused:
            fused = self._rerank(query, fused)
            method_details["reranking"] = {
                "model": self.cfg.rerank_model,
                "candidates_after_rerank": len(fused),
            }

        # Final truncation
        final = fused[:rerank_top_k]

        # Build output
        results = []
        for rank, item in enumerate(final):
            chunk = TextChunk(
                chunk_id=item["chunk_id"],
                document_id=item["metadata"]["document_id"],
                filename=item["metadata"]["filename"],
                page_number=item["metadata"]["page_number"],
                section=item["metadata"].get("section"),
                content=item["content"],
                token_count=len(item["content"]) // 4,
            )
            results.append(RetrievalResult(
                chunk=chunk,
                score=item["score"],
                retrieval_method="hybrid+rerank" if self.cfg.rerank_enabled else "hybrid",
                rank=rank,
            ))

        elapsed = (time.time() - start_time) * 1000

        return RetrievalOutput(
            query=query,
            candidates=results,
            total_candidates=len(results),
            retrieval_latency_ms=elapsed,
            method_details=method_details,
        )

    # ──────────────────────────────────────────
    # Stage 1: Dense retrieval
    # ──────────────────────────────────────────
    def _dense_retrieve(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """Semantic similarity search via vector index."""
        if top_k is None:
            top_k = self.cfg.dense_top_k
        query_embedding = self.embedder.embed_query(query)
        return self.vector_index.search(query_embedding, top_k=top_k)

    # ──────────────────────────────────────────
    # Stage 2: BM25 retrieval
    # ──────────────────────────────────────────
    def _bm25_retrieve(self, query: str, top_k: Optional[int] = None) -> list[dict]:
        """Lexical keyword search via BM25."""
        if top_k is None:
            top_k = self.cfg.bm25_top_k
        return self.bm25_index.search(query, top_k=top_k)

    # ──────────────────────────────────────────
    # Stage 3: Fusion methods
    # ──────────────────────────────────────────
    def _reciprocal_rank_fusion(
        self, dense: list[dict], bm25: list[dict]
    ) -> list[dict]:
        """
        Reciprocal Rank Fusion (RRF).

        Score = Σ 1/(k + rank_i) for each retrieval method i.

        RRF is parameter-free (except k), robust to score scale
        differences between retrievers, and well-documented in IR literature.

        Reference: Cormack et al., "Reciprocal Rank Fusion outperforms
        Condorcet and individual Rank Learning Methods" (2009).
        """
        from src.retrieval.rrf import reciprocal_rank_fusion
        return reciprocal_rank_fusion([dense, bm25], k=self.cfg.rrf_k)

    def _weighted_fusion(
        self,
        dense: list[dict],
        bm25: list[dict],
        dense_weight: Optional[float] = None,
        bm25_weight: Optional[float] = None,
    ) -> list[dict]:
        """
        Weighted score fusion.

        Requires score normalization (both scores mapped to [0,1]).

        Args:
            dense: Dense retrieval results
            bm25: BM25 retrieval results
            dense_weight: Weight for dense scores (defaults to config)
            bm25_weight: Weight for BM25 scores (defaults to config)
        """
        # Use provided weights or fall back to config
        if dense_weight is None:
            dense_weight = self.cfg.dense_weight
        if bm25_weight is None:
            bm25_weight = self.cfg.bm25_weight

        scores: dict[str, float] = defaultdict(float)
        items: dict[str, dict] = {}

        # Normalize dense scores to [0,1]
        max_dense = max((d["score"] for d in dense), default=1.0) or 1.0
        for item in dense:
            cid = item["chunk_id"]
            scores[cid] += (item["score"] / max_dense) * dense_weight
            items[cid] = item

        # Normalize BM25 scores to [0,1]
        max_bm25 = max((b["score"] for b in bm25), default=1.0) or 1.0
        for item in bm25:
            cid = item["chunk_id"]
            scores[cid] += (item["score"] / max_bm25) * bm25_weight
            if cid not in items:
                items[cid] = item

        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        return [{**items[cid], "score": scores[cid]} for cid in sorted_ids]

    def _interleave_fusion(
        self, dense: list[dict], bm25: list[dict]
    ) -> list[dict]:
        """Simple interleaving: alternate between dense and BM25 results."""
        seen = set()
        results = []
        max_len = max(len(dense), len(bm25))

        for i in range(max_len):
            if i < len(dense):
                cid = dense[i]["chunk_id"]
                if cid not in seen:
                    seen.add(cid)
                    results.append(dense[i])
            if i < len(bm25):
                cid = bm25[i]["chunk_id"]
                if cid not in seen:
                    seen.add(cid)
                    results.append(bm25[i])

        return results

    # ──────────────────────────────────────────
    # Stage 4: Reranking
    # ──────────────────────────────────────────
    def _rerank(self, query: str, candidates: list[dict]) -> list[dict]:
        """
        Cross-encoder reranking.

        Cross-encoders are more accurate than bi-encoders for
        relevance scoring because they process query+document together.

        Model: ms-marco-MiniLM (fast, good quality)
        """
        if self._reranker is None:
            from sentence_transformers import CrossEncoder
            self._reranker = CrossEncoder(self.cfg.rerank_model)

        # Build query-document pairs
        pairs = [(query, c["content"]) for c in candidates]
        rerank_scores = self._reranker.predict(pairs)

        # Update scores and sort
        for i, candidate in enumerate(candidates):
            candidate["score"] = float(rerank_scores[i])
            candidate["rerank_score"] = float(rerank_scores[i])

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates
