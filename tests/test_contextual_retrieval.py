"""
tests/test_contextual_retrieval.py — Unit tests for Anthropic Contextual Retrieval.
"""

import pytest
from src.core.models import TextChunk
from src.core.config import ChunkingConfig
from src.chunking.contextual_chunker import ContextualChunker
from src.chunking.chunker import get_chunker


@pytest.fixture
def sample_report_pages():
    page1 = TextChunk(
        document_id="doc-corp-10k",
        filename="Alphabet_10K_FY2024.pdf",
        page_number=0,
        content=(
            "Alphabet Inc. Annual Report Fiscal Year 2024.\n"
            "This report details Alphabet's consolidated revenues, operating income, and AI infrastructure investments.\n\n"
            "1. Executive Summary\n"
            "Total consolidated revenue reached $350 billion in 2024, up 15% year-over-year.\n"
            "Google Services and Google Cloud showed unprecedented momentum."
        ),
        token_count=50,
    )
    page2 = TextChunk(
        document_id="doc-corp-10k",
        filename="Alphabet_10K_FY2024.pdf",
        page_number=1,
        content=(
            "2. Google Cloud Segment Performance\n"
            "Cloud revenue accelerated to $40 billion, driven by enterprise adoption of Gemini and Vertex AI.\n"
            "Operating margins improved by 800 basis points due to tensor processing unit efficiencies."
        ),
        token_count=45,
    )
    return [page1, page2]


def test_contextual_chunker_factory():
    chunker = get_chunker("contextual")
    assert isinstance(chunker, ContextualChunker)


def test_situated_context_prepended(sample_report_pages):
    chunker = ContextualChunker()
    cfg = ChunkingConfig(chunk_size=100, chunk_overlap=20, min_chunk_size=10)
    chunks = chunker.chunk(sample_report_pages, cfg)

    assert len(chunks) > 0
    for chunk in chunks:
        # Anthropic situated context prefix check
        assert chunk.content.startswith("[Document:")
        assert "Alphabet_10K_FY2024.pdf" in chunk.content
        assert "Section:" in chunk.content
        assert "Scope:" in chunk.content
        # Metadata check
        assert chunk.metadata.get("chunk_strategy") == "contextual"
        assert "raw_content" in chunk.metadata
        assert "context_prefix" in chunk.metadata
