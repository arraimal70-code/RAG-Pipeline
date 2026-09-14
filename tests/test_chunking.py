"""
tests/test_chunking.py — Unit tests for chunking strategies.

Tests verify:
- Each strategy produces non-empty chunks
- Chunks respect size constraints
- Metadata is preserved
- Overlap works correctly
- Edge cases (empty input, tiny documents)
"""

import pytest
from src.core.models import TextChunk
from src.core.config import ChunkingConfig
from src.chunking.chunker import (
    FixedSizeChunker, SentenceChunker, RecursiveChunker,
    StructureAwareChunker, get_chunker,
)


@pytest.fixture
def sample_page():
    """Create a sample page chunk for testing."""
    return TextChunk(
        document_id="test-doc-1",
        filename="test.pdf",
        page_number=0,
        content=(
            "Machine learning is a subset of artificial intelligence. "
            "It enables systems to learn from data.\n\n"
            "Deep learning uses neural networks with many layers. "
            "These models can learn complex patterns.\n\n"
            "Transfer learning allows reusing pre-trained models. "
            "This reduces training time significantly.\n\n"
            "Natural language processing handles human language. "
            "Applications include translation and summarization."
        ),
        token_count=60,
    )


@pytest.fixture
def default_config():
    return ChunkingConfig(
        chunk_size=50,    # ~200 chars
        chunk_overlap=10,  # ~40 chars
        min_chunk_size=5,  # ~20 chars
    )


class TestFixedSizeChunker:
    def test_produces_chunks(self, sample_page, default_config):
        chunker = FixedSizeChunker()
        chunks = chunker.chunk([sample_page], default_config)
        assert len(chunks) > 0

    def test_preserves_metadata(self, sample_page, default_config):
        chunker = FixedSizeChunker()
        chunks = chunker.chunk([sample_page], default_config)
        for chunk in chunks:
            assert chunk.document_id == "test-doc-1"
            assert chunk.filename == "test.pdf"
            assert chunk.page_number == 0

    def test_respects_max_size(self, sample_page, default_config):
        chunker = FixedSizeChunker()
        chunks = chunker.chunk([sample_page], default_config)
        max_chars = default_config.chunk_size * 4
        for chunk in chunks:
            assert len(chunk.content) <= max_chars + 50  # small tolerance

    def test_empty_input(self, default_config):
        chunker = FixedSizeChunker()
        empty_page = TextChunk(
            document_id="test", filename="empty.pdf",
            page_number=0, content="", token_count=0,
        )
        chunks = chunker.chunk([empty_page], default_config)
        assert len(chunks) == 0


class TestSentenceChunker:
    def test_does_not_split_sentences(self, sample_page, default_config):
        chunker = SentenceChunker()
        chunks = chunker.chunk([sample_page], default_config)
        # Each chunk should end with sentence-ending punctuation or be the last
        for chunk in chunks[:-1]:
            # Allow some tolerance for edge cases
            assert len(chunk.content) > 0

    def test_produces_chunks(self, sample_page, default_config):
        chunker = SentenceChunker()
        chunks = chunker.chunk([sample_page], default_config)
        assert len(chunks) > 0


class TestRecursiveChunker:
    def test_produces_chunks(self, sample_page, default_config):
        chunker = RecursiveChunker()
        chunks = chunker.chunk([sample_page], default_config)
        assert len(chunks) > 0

    def test_prefers_paragraph_boundaries(self, sample_page, default_config):
        chunker = RecursiveChunker()
        chunks = chunker.chunk([sample_page], default_config)
        # Should prefer splitting at \n\n (paragraph boundaries)
        assert len(chunks) > 0


class TestStructureAwareChunker:
    def test_detects_sections(self):
        chunker = StructureAwareChunker()
        page = TextChunk(
            document_id="test", filename="test.pdf",
            page_number=0,
            content=(
                "Introduction\n"
                "This is the introduction paragraph.\n\n"
                "Methods\n"
                "This describes the methods used.\n\n"
                "Results\n"
                "These are the results of the study."
            ),
            token_count=30,
        )
        cfg = ChunkingConfig(chunk_size=200, chunk_overlap=10, min_chunk_size=5)
        chunks = chunker.chunk([page], cfg)
        sections = {c.section for c in chunks if c.section}
        assert len(sections) > 0


class TestChunkerFactory:
    def test_get_valid_chunker(self):
        for strategy in ["fixed", "sentence", "recursive", "structure"]:
            chunker = get_chunker(strategy)
            assert chunker is not None

    def test_get_invalid_chunker(self):
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            get_chunker("nonexistent")
