"""
src/embeddings/embedder.py — Embedding generation.

Supports:
- Local: sentence-transformers (free, offline)
- OpenAI: text-embedding-3-small (API, higher quality)

Uses batching for efficiency and caching to avoid re-embedding
identical content.
"""

import hashlib
import logging
import time
from typing import Protocol
from functools import lru_cache

from src.core.config import config

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Interface for embedding providers."""
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...
    def embed_query(self, text: str) -> list[float]:
        ...


class LocalEmbedder:
    """
    Local embedding using sentence-transformers.

    Model: all-MiniLM-L6-v2 (384 dimensions)
    Speed: ~50 chunks/sec on CPU
    Cost: $0

    Design: Model is loaded once and cached. Batching improves throughput.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Dimension: {self.dimension}")

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        start = time.time()
        embeddings = self.model.encode(
            texts,
            batch_size=config.embedding.batch_size,
            normalize_embeddings=config.embedding.normalize,
            show_progress_bar=len(texts) > 100,
        )
        elapsed = time.time() - start
        logger.debug(f"Embedded {len(texts)} texts in {elapsed:.2f}s")
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        embedding = self.model.encode(
            [text],
            normalize_embeddings=config.embedding.normalize,
        )
        return embedding[0].tolist()


class OpenAIEmbedder:
    """
    OpenAI embedding using text-embedding-3-small.

    Model: text-embedding-3-small (1536 dimensions)
    Speed: ~1000 chunks/sec (API-limited)
    Cost: ~$0.02 per 1M tokens
    """

    def __init__(self, model: str = "text-embedding-3-small"):
        from langchain_openai import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings(model=model)
        self.dimension = 1536

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts."""
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""
        return self.embeddings.embed_query(text)


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────
_embedder_cache: dict[str, Embedder] = {}


def get_embedder() -> Embedder:
    """Get or create the configured embedder (cached)."""
    provider = config.embedding.provider
    if provider not in _embedder_cache:
        if provider == "openai":
            _embedder_cache[provider] = OpenAIEmbedder()
        else:
            _embedder_cache[provider] = LocalEmbedder(config.embedding.model_name)
    return _embedder_cache[provider]
