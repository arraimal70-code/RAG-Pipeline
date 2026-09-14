"""
tests/test_config.py — Tests for configuration management.

Tests verify:
- Configuration validation
- Default values
- Override behavior
- Error handling for invalid configs
"""

import pytest
from src.core.config import AppConfig, ChunkingConfig, RetrievalConfig


class TestAppConfig:
    def test_default_config_valid(self):
        """Default configuration should be valid."""
        config = AppConfig()
        config.validate()  # Should not raise

    def test_invalid_chunk_overlap(self):
        """Chunk overlap must be less than chunk size."""
        config = AppConfig(
            chunking=ChunkingConfig(chunk_size=100, chunk_overlap=100)
        )
        with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
            config.validate()

    def test_invalid_rerank_top_k(self):
        """Rerank top-K must be <= post-fusion top-K."""
        config = AppConfig(
            retrieval=RetrievalConfig(
                post_fusion_top_k=10,
                rerank_top_k=20
            )
        )
        with pytest.raises(ValueError, match="rerank_top_k must be <= post_fusion_top_k"):
            config.validate()

    def test_invalid_weights(self):
        """Dense + BM25 weights must sum to 1.0."""
        config = AppConfig(
            retrieval=RetrievalConfig(
                dense_weight=0.5,
                bm25_weight=0.3
            )
        )
        with pytest.raises(ValueError, match="dense_weight \\+ bm25_weight must equal 1.0"):
            config.validate()

    def test_valid_weights(self):
        """Valid weights should pass validation."""
        config = AppConfig(
            retrieval=RetrievalConfig(
                dense_weight=0.7,
                bm25_weight=0.3
            )
        )
        config.validate()  # Should not raise


class TestChunkingConfig:
    def test_default_values(self):
        config = ChunkingConfig()
        assert config.strategy == "recursive"
        assert config.chunk_size == 512
        assert config.chunk_overlap == 64

    def test_custom_values(self):
        config = ChunkingConfig(
            strategy="fixed",
            chunk_size=256,
            chunk_overlap=32
        )
        assert config.strategy == "fixed"
        assert config.chunk_size == 256
        assert config.chunk_overlap == 32


class TestRetrievalConfig:
    def test_default_values(self):
        config = RetrievalConfig()
        assert config.dense_top_k == 50
        assert config.bm25_top_k == 50
        assert config.fusion_method == "rrf"
        assert config.rerank_enabled is True

    def test_custom_values(self):
        config = RetrievalConfig(
            dense_top_k=100,
            bm25_top_k=100,
            fusion_method="weighted",
            rerank_enabled=False
        )
        assert config.dense_top_k == 100
        assert config.fusion_method == "weighted"
        assert config.rerank_enabled is False
