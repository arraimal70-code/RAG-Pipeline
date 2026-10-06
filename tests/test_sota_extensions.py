"""
tests/test_sota_extensions.py — Comprehensive tests for SOTA research extensions:
1. HyDE (Hypothetical Document Embeddings)
2. CRAG (Corrective RAG Knowledge Refinement & Filtering)
3. Self-RAG Reflection Critique ([ISREL], [ISSUP], [ISUSE])
4. Sub-5ms Semantic Cache (Exact & Cosine Similarity Hits, LRU Eviction)
"""

import time
import pytest
from unittest.mock import MagicMock

from src.core.models import (
    TextChunk, RetrievalResult, RetrievalOutput, QueryResponse
)
from src.experimental.hyde import HypotheticalDocumentGenerator
from src.experimental.crag import CorrectiveRAGEngine, CRAGAction
from src.cache.semantic_cache import SemanticCache
from src.pipeline import RAGPipeline


class TestHyDE:
    def test_hypothetical_passage_generation_financial(self):
        generator = HypotheticalDocumentGenerator()
        query = "What was the total revenue in 2023?"
        passage = generator.generate_hypothetical_passage(query)
        assert isinstance(passage, str)
        assert len(passage) > 20
        assert "revenue" in passage.lower() or "2023" in passage

    def test_hypothetical_passage_generation_comparison(self):
        generator = HypotheticalDocumentGenerator()
        query = "Compare Apple vs Microsoft operating margins"
        passage = generator.generate_hypothetical_passage(query)
        assert isinstance(passage, str)
        assert "comparative" in passage.lower() or "comparing" in passage.lower()

    def test_generate_hyde_embedding(self):
        generator = HypotheticalDocumentGenerator()
        query = "What is quantum computing error mitigation?"
        emb = generator.generate_hyde_embedding(query)
        assert isinstance(emb, list)
        assert len(emb) == 384
        # Assert unit vector normalization
        norm = sum(x * x for x in emb) ** 0.5
        assert abs(norm - 1.0) < 1e-3


class TestCRAGAndSelfRAG:
    def _create_mock_retrieval(self, score: float, content: str) -> RetrievalOutput:
        chunk = TextChunk(
            chunk_id="chunk_crag_1",
            document_id="doc_crag_1",
            filename="10k.txt",
            page_number=1,
            content=content,
            metadata={"source": "10k.txt"},
            char_offset=0,
            token_count=len(content.split()),
        )
        candidate = RetrievalResult(
            chunk=chunk,
            score=score,
            retrieval_method="dense",
            rank=1,
        )
        return RetrievalOutput(
            query="test query",
            candidates=[candidate],
            total_candidates=1,
            retrieval_latency_ms=1.5,
        )

    def test_crag_action_correct(self):
        engine = CorrectiveRAGEngine(high_threshold=0.65, low_threshold=0.35)
        text = "Tesla reported net profit of $15 billion in 2023. Operating margins reached 16.8%."
        retrieval = self._create_mock_retrieval(score=0.85, content=text)
        assessment = engine.evaluate_retrieval("What was Tesla's net profit in 2023?", retrieval)

        assert assessment.action == CRAGAction.CORRECT
        assert assessment.confidence_score >= 0.65
        assert len(assessment.refined_strips) > 0

    def test_crag_action_ambiguous_and_rewrites(self):
        engine = CorrectiveRAGEngine(high_threshold=0.70, low_threshold=0.30)
        text = "General market conditions were favorable in North America."
        retrieval = self._create_mock_retrieval(score=0.45, content=text)
        assessment = engine.evaluate_retrieval("Specific microchip revenue segment breakdown", retrieval)

        assert assessment.action == CRAGAction.AMBIGUOUS
        assert len(assessment.query_rewrites) >= 2

    def test_crag_action_incorrect(self):
        engine = CorrectiveRAGEngine(high_threshold=0.65, low_threshold=0.35)
        retrieval = RetrievalOutput(
            query="unknown query",
            candidates=[],
            total_candidates=0,
            retrieval_latency_ms=0.5,
        )
        assessment = engine.evaluate_retrieval("unknown query", retrieval)
        assert assessment.action == CRAGAction.INCORRECT
        assert assessment.confidence_score == 0.0

    def test_self_rag_critique(self):
        engine = CorrectiveRAGEngine()
        query = "What was the operating revenue in 2024?"
        answer = "In 2024, operating revenue reached $42.5 billion [CITE:chunk_1]."
        chunk = TextChunk(
            chunk_id="chunk_1",
            document_id="doc_1",
            filename="annual.txt",
            page_number=1,
            content="In fiscal year 2024, operating revenue was reported at $42.5 billion.",
            metadata={"source": "annual.txt"},
            char_offset=0,
            token_count=12,
        )

        critique = engine.self_reflect_critique(query, answer, [chunk])
        assert critique.is_relevant is True
        assert critique.is_supported is True
        assert critique.utility_score >= 0.70


class TestSemanticCache:
    def test_exact_and_semantic_cache_hit(self):
        cache = SemanticCache(similarity_threshold=0.85, max_entries=10)

        response = QueryResponse(
            question="What is the net profit of Acme Corp?",
            answer="Acme Corp reported net profit of $50M in 2023.",
            support_level="fully_supported",
            confidence=0.95,
            citations=[],
            abstained=False,
        )

        cache.put("What is the net profit of Acme Corp?", response)

        # 1. Exact match hit
        hit1 = cache.get("What is the net profit of Acme Corp?")
        assert hit1 is not None
        assert hit1.answer == response.answer

        # 2. Semantic match hit (minor variation)
        hit2 = cache.get("what was the net profit for Acme Corp")
        assert hit2 is not None
        assert hit2.answer == response.answer

        # 3. Unrelated query miss
        miss = cache.get("Explain quantum entanglement in superconductors")
        assert miss is None

        # Stats check
        stats = cache.stats()
        assert stats["total_lookups"] == 3
        assert stats["total_hits"] == 2
        assert stats["hit_rate"] == pytest.approx(0.6667, rel=1e-2)

    def test_cache_lru_eviction(self):
        cache = SemanticCache(max_entries=2)
        resp = QueryResponse(
            question="q",
            answer="a",
            support_level="fully_supported",
            confidence=0.9,
            citations=[],
            abstained=False,
        )

        cache.put("q1", resp)
        cache.put("q2", resp)
        assert len(cache.entries) == 2

        # Insert 3rd entry, should evict q1
        cache.put("q3", resp)
        assert len(cache.entries) == 2
        assert "q1" not in cache.entries
        assert "q2" in cache.entries
        assert "q3" in cache.entries


def test_pipeline_integration_cache_and_hyde(pipeline, tmp_path):
    """Verify that full pipeline uses HyDE and caches validated answers."""
    doc_file = tmp_path / "acme_doc.txt"
    doc_file.write_text(
        "Acme Corp fiscal year 2023 total revenue was $100 million. Operating income was $20 million.",
        encoding="utf-8"
    )
    pipeline.ingest_document(str(doc_file))

    # First query with HyDE enabled
    resp1 = pipeline.query("What was Acme Corp total revenue in 2023?", use_cache=True, use_hyde=True)
    assert resp1 is not None
    assert not resp1.abstained
    assert "self_rag_critique" in resp1.retrieval_metadata
    assert "crag_action" in resp1.retrieval_metadata

    # Second query: exact same query should hit semantic cache in <50ms
    start_t = time.perf_counter()
    resp2 = pipeline.query("What was Acme Corp total revenue in 2023?", use_cache=True)
    lookup_ms = (time.perf_counter() - start_t) * 1000
    assert resp2 is not None
    assert resp2.answer == resp1.answer
    assert lookup_ms < 50.0  # Fast sub-50ms in local Python interpreter
