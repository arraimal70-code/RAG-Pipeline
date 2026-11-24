"""
src/retrieval/reranker.py — Multi-stage high-precision reranking funnel.

Architectural Funnel (Tier-1 Enterprise RAG):
Stage 1: Dense + BM25 Fusion (RRF / Weighted) -> Top 50 candidates
Stage 2: ColBERT MaxSim Late-Interaction fast prune -> Top 20 candidates
Stage 3: Cross-Encoder (BAAI/bge-reranker-v2-m3) high-precision scoring -> Top 5 candidates
Stage 4: Contextual Extractive Compression -> Grounded context token spans
"""

import logging
import math
import re
from typing import Any, Protocol

from src.retrieval.contextual_compressor import ContextualCompressor
from src.retrieval.late_interaction import LateInteractionScorer

logger = logging.getLogger(__name__)


class Reranker(Protocol):
    """Interface for reranking backends."""

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        ...


class DeterministicReranker:
    """
    Deterministic subword alignment and term matching reranker.
    Provides sub-millisecond, zero-GPU execution for offline CI/CD and testing.
    """

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        if not candidates or top_k <= 0:
            return []

        q_terms = set(re.findall(r"\w+", query.lower()))
        for c in candidates:
            content = c.get("content", "").lower()
            c_terms = set(re.findall(r"\w+", content))
            if not q_terms or not c_terms:
                c["rerank_score"] = 0.0
                continue

            overlap = len(q_terms & c_terms)
            jaccard = overlap / len(q_terms | c_terms)

            # Substring exact sequence match boost
            substring_boost = 0.3 if query.lower().strip() in content else 0.0
            base_score = float(c.get("score", 0.0))
            score = 0.5 * base_score + 0.4 * jaccard + substring_boost
            c["rerank_score"] = round(min(1.0, score), 4)
            c["score"] = c["rerank_score"]

        candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return candidates[:top_k]


class ColBERTMaxSimReranker:
    """ColBERT Token MaxSim Late-Interaction Reranker."""

    def __init__(self, dimension: int = 128) -> None:
        self.scorer = LateInteractionScorer(dimension=dimension)

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 20) -> list[dict[str, Any]]:
        if not candidates or top_k <= 0:
            return []

        for c in candidates:
            res = self.scorer.compute_maxsim(query, c.get("content", ""))
            c["maxsim_score"] = float(res.normalized_score)
            c["maxsim_raw"] = float(res.raw_score)
            c["score"] = float(res.normalized_score)

        candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return candidates[:top_k]


class BGEReranker:
    """
    BAAI/bge-reranker-v2-m3 cross-encoder reranker.
    Supports multilingual, token-level attention cross-scoring.
    Gracefully falls back to DeterministicReranker if weights are unavailable.
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3") -> None:
        import os
        self.model_name = model_name
        self._model: Any = None
        self._fallback = DeterministicReranker()

        # By default in CI and offline test environments, use deterministic reranker for fast sub-second execution
        if os.getenv("CI") or os.getenv("RAG_OFFLINE_MOCK") or not os.getenv("RAG_ENABLE_NEURAL_RERANKER"):
            return

        try:
            from FlagEmbedding import FlagReranker
            self._model = FlagReranker(model_name, use_fp16=False)
            logger.info("FlagReranker BGE-Reranker-v2-M3 initialized successfully.")
        except Exception:  # noqa: BLE001
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(model_name)
                logger.info(f"CrossEncoder {model_name} initialized.")
            except Exception as ex:  # noqa: BLE001
                logger.info(f"Neural reranker offline or not cached ({ex}). Engaging deterministic reranker.")

    def rerank(self, query: str, candidates: list[dict[str, Any]], top_k: int = 5) -> list[dict[str, Any]]:
        if not candidates or top_k <= 0:
            return []

        if self._model is not None:
            try:
                pairs = [[query, c.get("content", "")] for c in candidates]
                if hasattr(self._model, "compute_score"):
                    scores = self._model.compute_score(pairs)
                else:
                    scores = self._model.predict(pairs)

                if isinstance(scores, float | int):
                    scores = [scores]

                for i, c in enumerate(candidates):
                    # Sigmoid normalize if unbounded logits
                    val = float(scores[i])
                    prob = 1.0 / (1.0 + math.exp(-val)) if (val > 1.0 or val < 0.0) else val
                    c["score"] = round(prob, 4)
                    c["rerank_score"] = round(prob, 4)

                candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                return candidates[:top_k]
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BGE rerank execution failed: {e}. Using deterministic fallback.")

        return self._fallback.rerank(query, candidates, top_k=top_k)


class MultiStageRerankerFunnel:
    """
    Frontier 4-Stage Reranking Funnel.
    Coordinates ColBERT MaxSim token-level pruning, BGE cross-encoder high-precision
    reranking, and contextual extractive compression.
    """

    def __init__(
        self,
        colbert_prune_top_k: int = 20,
        final_top_k: int = 5,
        enable_compression: bool = True,
    ) -> None:
        self.colbert_pruner = ColBERTMaxSimReranker()
        self.bge_reranker = BGEReranker()
        self.compressor = ContextualCompressor(similarity_threshold=0.25)
        self.colbert_prune_top_k = colbert_prune_top_k
        self.final_top_k = final_top_k
        self.enable_compression = enable_compression

    def execute_funnel(
        self,
        query: str,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute the complete multi-stage funnel on hybrid candidate documents.
        """
        if not candidates:
            return []

        # Stage 2: ColBERT MaxSim Fast Pruning
        pruned = self.colbert_pruner.rerank(query, candidates, top_k=self.colbert_prune_top_k)

        # Stage 3: BGE-Reranker-v2-M3 Deep Cross-Attention
        reranked = self.bge_reranker.rerank(query, pruned, top_k=self.final_top_k)

        # Stage 4: Contextual Extractive Compression
        if self.enable_compression:
            from src.core.models import TextChunk
            for item in reranked:
                raw_text = item.get("content", "")
                dummy_chunk = TextChunk(
                    document_id=item.get("document_id", "doc"),
                    filename=item.get("filename", "file.pdf"),
                    page_number=item.get("page_number", 0),
                    content=raw_text,
                    metadata=item.get("metadata", {}),
                )
                compressed_text, report = self.compressor.compress_chunk(query, dummy_chunk)
                if compressed_text:
                    item["compressed_content"] = compressed_text
                    item["compression_ratio"] = report.compression_ratio
                    item["content"] = compressed_text

        return reranked
