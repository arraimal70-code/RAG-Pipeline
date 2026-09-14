"""
tests/test_integration.py — End-to-end integration tests.

Tests the complete pipeline from document ingestion to query answering.
"""

import pytest
import tempfile
from pathlib import Path
from pypdf import PdfWriter, PdfReader
from pypdf.generic import RectangleObject

from src.pipeline import RAGPipeline
from src.core.models import SupportLevel


@pytest.fixture
def sample_pdf(tmp_path):
    """Create a sample PDF for testing."""
    pdf_path = tmp_path / "test_document.pdf"

    # Create a simple PDF with known content
    writer = PdfWriter()

    # Page 1: Financial data
    writer.add_blank_page(width=612, height=792)
    page1 = writer.pages[0]
    # Note: PyPDF can't add text directly, so we'll create a minimal PDF
    # For real tests, use actual PDF files

    # For now, create a minimal valid PDF
    with open(pdf_path, "wb") as f:
        writer.write(f)

    return pdf_path


@pytest.fixture
def pipeline():
    """Create a pipeline instance for testing."""
    return RAGPipeline()


class TestPipelineIntegration:
    """Integration tests for the complete pipeline."""

    def test_pipeline_initialization(self, pipeline):
        """Test that pipeline initializes all components."""
        assert pipeline.parser is not None
        assert pipeline.embedder is not None
        assert pipeline.vector_index is not None
        assert pipeline.bm25_index is not None
        assert pipeline.query_analyzer is not None
        assert pipeline.retriever is not None
        assert pipeline.numerical_reasoner is not None
        assert pipeline.temporal_reasoner is not None
        assert pipeline.evidence_checker is not None
        assert pipeline.generator is not None
        assert pipeline.citation_validator is not None
        assert pipeline.claim_extractor is not None

    def test_pipeline_stats(self, pipeline):
        """Test that pipeline returns statistics."""
        stats = pipeline.get_stats()
        assert "vector_index_size" in stats
        assert "bm25_index_size" in stats
        assert "config" in stats
        assert isinstance(stats["vector_index_size"], int)
        assert isinstance(stats["bm25_index_size"], int)


class TestQueryAnalysis:
    """Test query analysis and classification."""

    def test_classify_numerical_query(self, pipeline):
        """Test classification of numerical queries."""
        query_type = pipeline.query_analyzer.classify("What was the revenue in 2023?")
        assert query_type.value == "numerical"

    def test_classify_comparison_query(self, pipeline):
        """Test classification of comparison queries."""
        query_type = pipeline.query_analyzer.classify("Compare Q1 and Q2 results")
        assert query_type.value == "comparison"

    def test_classify_conceptual_query(self, pipeline):
        """Test classification of conceptual queries."""
        query_type = pipeline.query_analyzer.classify("What is the company's strategy?")
        assert query_type.value in ["conceptual", "unknown"]


class TestEvidenceSufficiency:
    """Test evidence sufficiency assessment."""

    def test_empty_retrieval_abstains(self, pipeline):
        """Test that empty retrieval results in abstention."""
        from src.core.models import RetrievalOutput

        retrieval = RetrievalOutput(
            query="test",
            candidates=[],
            total_candidates=0,
            retrieval_latency_ms=0.0,
        )

        assessment = pipeline.evidence_checker.assess("test question", retrieval)
        assert not assessment.is_sufficient
        assert assessment.recommendation == "abstain"


class TestNumericalReasoning:
    """Test numerical reasoning integration."""

    def test_extract_numbers(self, pipeline):
        """Test numerical value extraction."""
        from src.core.models import TextChunk

        chunk = TextChunk(
            chunk_id="test",
            document_id="doc1",
            filename="test.pdf",
            page_number=0,
            content="Revenue was $100 million in FY2023.",
            token_count=10,
        )

        values = pipeline.numerical_reasoner.extract_values([chunk])
        assert len(values) > 0
        assert any(v.value == 100_000_000 for v in values)


class TestTemporalReasoning:
    """Test temporal reasoning integration."""

    def test_extract_temporal_context(self, pipeline):
        """Test temporal context extraction."""
        contexts = pipeline.temporal_reasoner.extract_temporal_context(
            "Revenue in FY2023 was $100M"
        )
        assert len(contexts) > 0
        assert any(ctx.year == 2023 for ctx in contexts)

    def test_query_temporal_requirements(self, pipeline):
        """Test extraction of query temporal requirements."""
        reqs = pipeline.temporal_reasoner.extract_query_temporal_requirements(
            "What was revenue in FY2023?"
        )
        assert reqs["required_year"] == 2023


class TestCitationValidation:
    """Test citation validation."""

    def test_validate_citations(self, pipeline):
        """Test citation validation."""
        from src.core.models import (
            GenerationOutput, RetrievalOutput, RetrievalResult,
            TextChunk, Citation,
        )

        chunk = TextChunk(
            chunk_id="chunk1",
            document_id="doc1",
            filename="test.pdf",
            page_number=0,
            content="Revenue was $100 million.",
            token_count=10,
        )

        retrieval = RetrievalOutput(
            query="test",
            candidates=[
                RetrievalResult(chunk=chunk, score=0.9, retrieval_method="dense", rank=0)
            ],
            total_candidates=1,
            retrieval_latency_ms=0.0,
        )

        generation = GenerationOutput(
            answer="Revenue was $100 million.",
            support_level=SupportLevel.SUPPORTED,
            confidence=0.9,
            citations=[
                Citation(
                    document_id="doc1",
                    filename="test.pdf",
                    page_number=0,
                    chunk_id="chunk1",
                    relevant_text="Revenue was $100 million.",
                )
            ],
        )

        validated = pipeline.citation_validator.validate_citations(generation, retrieval)
        assert len(validated.citations) > 0
        assert all(c.validated for c in validated.citations)


class TestClaimExtraction:
    """Test claim-level analysis."""

    def test_extract_claims(self, pipeline):
        """Test claim extraction from answer."""
        answer = "Revenue was $100 million. Profit increased by 10%."
        claims = pipeline.claim_extractor.extract_claims(answer)
        assert len(claims) >= 1

    def test_evaluate_faithfulness(self, pipeline):
        """Test faithfulness evaluation."""
        from src.core.models import (
            GenerationOutput, RetrievalOutput, RetrievalResult,
            TextChunk,
        )

        chunk = TextChunk(
            chunk_id="chunk1",
            document_id="doc1",
            filename="test.pdf",
            page_number=0,
            content="Revenue was $100 million in FY2023.",
            token_count=10,
        )

        retrieval = RetrievalOutput(
            query="test",
            candidates=[
                RetrievalResult(chunk=chunk, score=0.9, retrieval_method="dense", rank=0)
            ],
            total_candidates=1,
            retrieval_latency_ms=0.0,
        )

        generation = GenerationOutput(
            answer="Revenue was $100 million.",
            support_level=SupportLevel.SUPPORTED,
            confidence=0.9,
            citations=[],
        )

        report = pipeline.claim_extractor.evaluate_faithfulness(generation, retrieval)
        assert report.total_claims >= 1
        assert 0.0 <= report.claim_level_faithfulness <= 1.0


class TestRetrieval:
    """Test retrieval components."""

    def test_hybrid_retrieval_initialization(self, pipeline):
        """Test that hybrid retriever initializes."""
        assert pipeline.retriever is not None
        assert pipeline.retriever.vector_index is not None
        assert pipeline.retriever.bm25_index is not None


class TestEndToEnd:
    """End-to-end pipeline tests."""

    @pytest.mark.skip(reason="Requires actual PDF documents and API keys")
    def test_full_pipeline_with_document(self, pipeline, sample_pdf):
        """Test complete pipeline with document ingestion and query."""
        # This test requires:
        # 1. Real PDF documents
        # 2. OpenAI API key
        # 3. Sufficient compute for embeddings

        # Ingest document
        result = pipeline.ingest_document(sample_pdf)
        assert result["num_chunks"] > 0

        # Query
        response = pipeline.query("What was the revenue?")
        assert response.question == "What was the revenue?"
        # Response will depend on document content

    def test_pipeline_handles_empty_index(self, pipeline):
        """Test that pipeline handles empty index gracefully."""
        # Query with no documents ingested
        response = pipeline.query("What was the revenue?")

        # Should either abstain or return low confidence
        assert response.abstained or response.confidence < 0.5


class TestTracing:
    """Test observability and tracing."""

    def test_trace_creation(self, pipeline):
        """Test that traces are created."""
        from src.observability.tracing import tracer

        trace = tracer.start_trace("test query")
        assert trace.query == "test query"
        assert trace.trace_id is not None

        trace.add_event("test_stage", {"test": "data"})
        assert len(trace.events) == 1

        tracer.end_trace(trace)
        assert trace.end_time is not None
