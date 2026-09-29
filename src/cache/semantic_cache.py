"""
src/cache/semantic_cache.py — Ultra-Low-Latency Semantic Query Cache.

Caches query embeddings and validated responses. When a semantically equivalent
query arrives (cosine similarity >= threshold), serves the response in <5ms,
bypassing redundant retrieval and inference steps.
"""

import time
import math
import logging
from typing import Optional, Dict, Any, List
from collections import OrderedDict
from dataclasses import dataclass

from src.core.models import QueryResponse
from src.embeddings.embedder import Embedder, get_embedder

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    query: str
    query_vector: List[float]
    response: QueryResponse
    created_at: float
    hits: int = 0


class SemanticCache:
    """
    In-memory semantic cache using embedding cosine similarity and LRU eviction.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_entries: int = 500,
        ttl_seconds: float = 3600.0,
        embedder: Optional[Embedder] = None,
    ):
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.embedder = embedder or get_embedder()
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self.total_lookups = 0
        self.total_hits = 0

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between vectors."""
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return sum(x * y for x, y in zip(a, b)) / (norm_a * norm_b)

    def get(self, query: str) -> Optional[QueryResponse]:
        """
        Lookup response for query. First checks exact match, then semantic similarity.
        """
        self.total_lookups += 1
        now = time.time()
        clean_q = query.strip().lower()

        # 1. Exact string match
        if clean_q in self.entries:
            entry = self.entries[clean_q]
            if now - entry.created_at < self.ttl_seconds:
                entry.hits += 1
                self.total_hits += 1
                self.entries.move_to_end(clean_q)
                logger.info(f"Semantic Cache: Exact hit for '{clean_q[:30]}...'")
                return entry.response
            else:
                del self.entries[clean_q]

        # 2. Semantic similarity search
        query_vec = self.embedder.embed_query(query)
        best_score = -1.0
        best_key = None

        for key, entry in self.entries.items():
            if now - entry.created_at >= self.ttl_seconds:
                continue
            sim = self._cosine_similarity(query_vec, entry.query_vector)
            if sim > best_score:
                best_score = sim
                best_key = key

        if best_score >= self.threshold and best_key:
            entry = self.entries[best_key]
            entry.hits += 1
            self.total_hits += 1
            self.entries.move_to_end(best_key)
            logger.info(f"Semantic Cache: Semantic hit ({best_score:.3f}) for '{clean_q[:30]}...'")
            return entry.response

        return None

    def put(self, query: str, response: QueryResponse) -> None:
        """
        Store a verified query response in the semantic cache.
        """
        clean_q = query.strip().lower()
        now = time.time()

        # Enforce LRU capacity limit
        if len(self.entries) >= self.max_entries:
            self.entries.popitem(last=False)

        query_vec = self.embedder.embed_query(query)
        entry = CacheEntry(
            query=query,
            query_vector=query_vec,
            response=response,
            created_at=now,
        )
        self.entries[clean_q] = entry
        self.entries.move_to_end(clean_q)

    def clear(self) -> None:
        """Clear all cache entries."""
        self.entries.clear()
        self.total_lookups = 0
        self.total_hits = 0

    def stats(self) -> Dict[str, Any]:
        """Return cache operational metrics."""
        hit_rate = (self.total_hits / self.total_lookups) if self.total_lookups > 0 else 0.0
        return {
            "entries_count": len(self.entries),
            "max_entries": self.max_entries,
            "total_lookups": self.total_lookups,
            "total_hits": self.total_hits,
            "hit_rate": round(hit_rate, 4),
        }
