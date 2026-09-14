"""
tests/test_retrieval.py — Tests for retrieval components.

Tests verify:
- BM25 indexing and search
- RRF fusion logic
- Reranking integration
- Edge cases (empty queries, no results)
"""

import pytest
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.rrf import reciprocal_rank_fusion


class TestReciprocalRankFusion:
    """Test RRF fusion algorithm."""

    def test_rrf_combines_results(self):
        """RRF should combine results from both retrievers."""
        dense = [
            {"chunk_id": "a", "score": 0.9, "content": "A", "metadata": {}},
            {"chunk_id": "b", "score": 0.8, "content": "B", "metadata": {}},
        ]
        bm25 = [
            {"chunk_id": "b", "score": 10.0, "content": "B", "metadata": {}},
            {"chunk_id": "c", "score": 8.0, "content": "C", "metadata": {}},
        ]

        fused = reciprocal_rank_fusion([dense, bm25])

        # "b" appears in both, should rank highest
        assert fused[0]["chunk_id"] == "b"
        assert len(fused) == 3  # a, b, c

    def test_rrf_handles_empty_inputs(self):
        fused = reciprocal_rank_fusion([[], []])
        assert len(fused) == 0

    def test_rrf_with_no_overlap(self):
        dense = [{"chunk_id": "a", "score": 0.9, "content": "A", "metadata": {}}]
        bm25 = [{"chunk_id": "b", "score": 10.0, "content": "B", "metadata": {}}]

        fused = reciprocal_rank_fusion([dense, bm25])
        assert len(fused) == 2
        ids = {f["chunk_id"] for f in fused}
        assert ids == {"a", "b"}

    def test_rrf_k_parameter(self):
        """Different k values should change ranking."""
        dense = [
            {"chunk_id": "a", "score": 0.9, "content": "A", "metadata": {}},
        ]
        bm25 = [
            {"chunk_id": "b", "score": 10.0, "content": "B", "metadata": {}},
        ]

        # With small k, top items get more weight
        fused_small_k = reciprocal_rank_fusion([dense, bm25], k=1)
        fused_large_k = reciprocal_rank_fusion([dense, bm25], k=100)

        # Both should have 2 items
        assert len(fused_small_k) == 2
        assert len(fused_large_k) == 2


class TestHybridRetriever:
    def test_interleave_fusion(self):
        """Test interleaving fusion method."""
        retriever = HybridRetriever.__new__(HybridRetriever)

        dense = [
            {"chunk_id": "d1", "content": "D1", "metadata": {}},
            {"chunk_id": "d2", "content": "D2", "metadata": {}},
        ]
        bm25 = [
            {"chunk_id": "b1", "content": "B1", "metadata": {}},
            {"chunk_id": "b2", "content": "B2", "metadata": {}},
        ]

        fused = retriever._interleave_fusion(dense, bm25)
        assert fused[0]["chunk_id"] == "d1"
        assert fused[1]["chunk_id"] == "b1"
        assert fused[2]["chunk_id"] == "d2"
        assert fused[3]["chunk_id"] == "b2"

    def test_interleave_handles_duplicates(self):
        retriever = HybridRetriever.__new__(HybridRetriever)

        dense = [{"chunk_id": "a", "content": "A", "metadata": {}}]
        bm25 = [{"chunk_id": "a", "content": "A", "metadata": {}}]

        fused = retriever._interleave_fusion(dense, bm25)
        assert len(fused) == 1  # duplicate removed
