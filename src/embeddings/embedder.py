"""
src/embeddings/embedder.py — Pluggable multi-vector embedding generation.

Supports Frontier Tier-1 multi-vector paradigms:
- BGE-M3: BAAI/bge-m3 dense (1024-d), sparse lexical weights, and ColBERT multi-vectors.
- Local: sentence-transformers (all-MiniLM-L6-v2, 384-d).
- OpenAI: text-embedding-3-small (1536-d).
- Deterministic: Ultra-fast semantic hash embedding for offline CI/CD and unit testing.
"""

import hashlib
import logging
import math
import re
import time
from collections import Counter
from typing import Any, Protocol

from src.core.config import config

logger = logging.getLogger(__name__)


class Embedder(Protocol):
    """Interface for embedding providers with multi-vector capabilities."""
    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...

    def embed_sparse(self, texts: list[str]) -> list[dict[str, float]]:
        ...

    def embed_colbert(self, texts: list[str]) -> list[list[list[float]]]:
        ...

    def embed_multi_vector(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, float]], list[list[list[float]]]]:
        ...

    def embed_query_multi_vector(
        self, text: str
    ) -> tuple[list[float], dict[str, float], list[list[float]]]:
        ...


class DeterministicTermVectorEmbedder:
    """
    Deterministic semantic hash embedding for offline testing, CI/CD, and lightweight deployment.

    Produces dense normalized vectors, sparse lexical weights, and per-token ColBERT representations
    without requiring heavy external neural networks or GPUs.
    """

    def __init__(self, dimension: int = 384, colbert_dim: int = 128) -> None:
        self.dimension = dimension
        self.colbert_dim = colbert_dim

    def _hash_token(self, token: str, seed: int = 0) -> int:
        h = hashlib.sha256(f"{seed}:{token}".encode()).digest()
        return int.from_bytes(h[:4], "little") % self.dimension

    def _hash_token_colbert(self, token: str, seed: int = 0) -> int:
        h = hashlib.sha256(f"{seed}:{token}".encode()).digest()
        return int.from_bytes(h[:4], "little") % self.colbert_dim

    def _text_to_vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        clean = text.lower().strip()
        tokens = re.findall(r"\w+", clean)
        if not tokens:
            return vec

        counts = Counter(tokens)
        total_tokens = len(tokens)

        # 1. Word token hashing with TF weighting
        for token, count in counts.items():
            tf = math.log1p(count) / total_tokens
            idx1 = self._hash_token(token, 0)
            idx2 = self._hash_token(token, 1)
            sign = 1.0 if (self._hash_token(token, 2) % 2 == 0) else -1.0
            vec[idx1] += tf
            vec[idx2] += tf * sign * 0.5

        # 2. Subword character 3-grams for morphological match
        for i in range(len(clean) - 2):
            ngram = clean[i:i + 3]
            idx = self._hash_token(ngram, 7)
            vec[idx] += 0.2 / (len(clean) + 1)

        # 3. L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 1e-9:
            vec = [v / norm for v in vec]
        return vec

    def _text_to_sparse(self, text: str) -> dict[str, float]:
        tokens = re.findall(r"\w+", text.lower().strip())
        if not tokens:
            return {}
        counts = Counter(tokens)
        total = len(tokens)
        return {tok: round(math.log1p(cnt) / total, 4) for tok, cnt in counts.items()}

    def _text_to_colbert(self, text: str, max_tokens: int = 64) -> list[list[float]]:
        tokens = re.findall(r"\w+", text.lower().strip())[:max_tokens]
        if not tokens:
            return [[0.0] * self.colbert_dim]

        token_vecs: list[list[float]] = []
        for tok in tokens:
            tvec = [0.0] * self.colbert_dim
            for s in range(3):
                idx = self._hash_token_colbert(tok, s)
                tvec[idx] += 1.0 / (s + 1)
            norm = math.sqrt(sum(v * v for v in tvec))
            if norm > 1e-9:
                tvec = [v / norm for v in tvec]
            token_vecs.append(tvec)
        return token_vecs

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._text_to_vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._text_to_vector(text)

    def embed_sparse(self, texts: list[str]) -> list[dict[str, float]]:
        return [self._text_to_sparse(t) for t in texts]

    def embed_colbert(self, texts: list[str]) -> list[list[list[float]]]:
        return [self._text_to_colbert(t) for t in texts]

    def embed_multi_vector(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, float]], list[list[list[float]]]]:
        dense = self.embed(texts)
        sparse = self.embed_sparse(texts)
        colbert = self.embed_colbert(texts)
        return dense, sparse, colbert

    def embed_query_multi_vector(
        self, text: str
    ) -> tuple[list[float], dict[str, float], list[list[float]]]:
        dense = self.embed_query(text)
        sparse = self._text_to_sparse(text)
        colbert = self._text_to_colbert(text)
        return dense, sparse, colbert


class BGEM3Embedder:
    """
    BAAI/bge-m3 multi-vector embedder supporting dense, sparse lexical, and ColBERT late-interaction.
    Gracefully falls back to deterministic multi-vector generation when offline or PyTorch is headless.
    """

    def __init__(self, model_name: str = "BAAI/bge-m3", dimension: int = 1024) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.colbert_dim = 128
        self._model: Any = None
        self._fallback = DeterministicTermVectorEmbedder(dimension=dimension, colbert_dim=self.colbert_dim)

        try:
            from FlagEmbedding import BGEM3FlagModel
            self._model = BGEM3FlagModel(model_name, use_fp16=False)
            logger.info("BGEM3FlagModel loaded successfully.")
        except Exception as e:  # noqa: BLE001
            logger.info(f"FlagEmbedding BGEM3FlagModel not initialized ({e}). Using robust multi-vector engine.")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is not None:
            try:
                res = self._model.encode(texts, return_dense=True, return_sparse=False, return_colbert_vecs=False)
                return res["dense_vecs"].tolist()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BGE-M3 encode dense failed: {e}. Falling back.")
        return self._fallback.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embed([text])[0]

    def embed_sparse(self, texts: list[str]) -> list[dict[str, float]]:
        if self._model is not None:
            try:
                res = self._model.encode(texts, return_dense=False, return_sparse=True, return_colbert_vecs=False)
                return [{str(k): float(v) for k, v in item.items()} for item in res["lexical_weights"]]
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BGE-M3 sparse extraction failed: {e}. Falling back.")
        return self._fallback.embed_sparse(texts)

    def embed_colbert(self, texts: list[str]) -> list[list[list[float]]]:
        if self._model is not None:
            try:
                res = self._model.encode(texts, return_dense=False, return_sparse=False, return_colbert_vecs=True)
                return [v.tolist() for v in res["colbert_vecs"]]
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BGE-M3 ColBERT extraction failed: {e}. Falling back.")
        return self._fallback.embed_colbert(texts)

    def embed_multi_vector(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, float]], list[list[list[float]]]]:
        if self._model is not None:
            try:
                res = self._model.encode(texts, return_dense=True, return_sparse=True, return_colbert_vecs=True)
                dense = res["dense_vecs"].tolist()
                sparse = [{str(k): float(v) for k, v in item.items()} for item in res["lexical_weights"]]
                colbert = [v.tolist() for v in res["colbert_vecs"]]
                return dense, sparse, colbert
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BGE-M3 multi-vector encode failed: {e}. Falling back.")
        return self._fallback.embed_multi_vector(texts)

    def embed_query_multi_vector(
        self, text: str
    ) -> tuple[list[float], dict[str, float], list[list[float]]]:
        dense, sparse, colbert = self.embed_multi_vector([text])
        return dense[0], sparse[0], colbert[0]


class LocalEmbedder:
    """
    Local embedding using sentence-transformers (e.g. all-MiniLM-L6-v2, 384 dimensions).
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        if hasattr(self.model, "get_embedding_dimension"):
            self.dimension: int = int(self.model.get_embedding_dimension())
        else:
            self.dimension = int(self.model.get_sentence_embedding_dimension())
        self._fallback = DeterministicTermVectorEmbedder(dimension=self.dimension)
        logger.info(f"Model loaded. Dimension: {self.dimension}")

    def embed(self, texts: list[str]) -> list[list[float]]:
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
        embedding = self.model.encode(
            [text],
            normalize_embeddings=config.embedding.normalize,
        )
        return embedding[0].tolist()

    def embed_sparse(self, texts: list[str]) -> list[dict[str, float]]:
        return self._fallback.embed_sparse(texts)

    def embed_colbert(self, texts: list[str]) -> list[list[list[float]]]:
        return self._fallback.embed_colbert(texts)

    def embed_multi_vector(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, float]], list[list[list[float]]]]:
        dense = self.embed(texts)
        sparse = self.embed_sparse(texts)
        colbert = self.embed_colbert(texts)
        return dense, sparse, colbert

    def embed_query_multi_vector(
        self, text: str
    ) -> tuple[list[float], dict[str, float], list[list[float]]]:
        dense = self.embed_query(text)
        sparse = self._fallback._text_to_sparse(text)
        colbert = self._fallback._text_to_colbert(text)
        return dense, sparse, colbert


class OpenAIEmbedder:
    """
    OpenAI embedding using text-embedding-3-small (1536 dimensions).
    """

    def __init__(self, model: str = "text-embedding-3-small") -> None:
        from langchain_openai import OpenAIEmbeddings
        self.embeddings = OpenAIEmbeddings(model=model, api_key=config.openai_api_key)
        self.dimension = 1536
        self._fallback = DeterministicTermVectorEmbedder(dimension=self.dimension)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> list[float]:
        return self.embeddings.embed_query(text)

    def embed_sparse(self, texts: list[str]) -> list[dict[str, float]]:
        return self._fallback.embed_sparse(texts)

    def embed_colbert(self, texts: list[str]) -> list[list[list[float]]]:
        return self._fallback.embed_colbert(texts)

    def embed_multi_vector(
        self, texts: list[str]
    ) -> tuple[list[list[float]], list[dict[str, float]], list[list[list[float]]]]:
        dense = self.embed(texts)
        sparse = self.embed_sparse(texts)
        colbert = self.embed_colbert(texts)
        return dense, sparse, colbert

    def embed_query_multi_vector(
        self, text: str
    ) -> tuple[list[float], dict[str, float], list[list[float]]]:
        dense = self.embed_query(text)
        sparse = self._fallback._text_to_sparse(text)
        colbert = self._fallback._text_to_colbert(text)
        return dense, sparse, colbert


# ──────────────────────────────────────────────
# Factory
# ──────────────────────────────────────────────
_embedder_cache: dict[str, Embedder] = {}


def get_embedder() -> Embedder:
    """Get or create the configured embedder (cached)."""
    provider = config.embedding.provider
    if provider not in _embedder_cache:
        if provider == "bge_m3" or config.embedding.model_name == "BAAI/bge-m3":
            _embedder_cache[provider] = BGEM3Embedder(
                model_name=config.embedding.model_name,
                dimension=config.embedding.dimension if config.embedding.dimension == 1024 else 1024,
            )
        elif provider == "openai" and config.openai_api_key:
            try:
                _embedder_cache[provider] = OpenAIEmbedder()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to initialize OpenAIEmbedder ({e}). Falling back to deterministic.")
                _embedder_cache[provider] = DeterministicTermVectorEmbedder(dimension=config.embedding.dimension)
        elif provider == "local":
            try:
                _embedder_cache[provider] = LocalEmbedder(config.embedding.model_name)
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Could not load SentenceTransformer ({e}). Falling back to DeterministicTermVectorEmbedder.")
                _embedder_cache[provider] = DeterministicTermVectorEmbedder(dimension=config.embedding.dimension)
        else:
            _embedder_cache[provider] = DeterministicTermVectorEmbedder(dimension=config.embedding.dimension)
    return _embedder_cache[provider]
