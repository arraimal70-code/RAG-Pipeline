"""
src/cache/semantic_cache.py — Enterprise Ultra-Low-Latency Semantic Query Cache.

Supports:
- Redis backend (via REDIS_URL environment variable or config)
- In-memory OrderedDict LRU fallback when Redis is unreachable or offline
- Multi-tenant cache key partitioning (`tenant_id`)
- Cosine similarity matching over query embeddings (threshold >= 0.85)
"""

import json
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from src.core.models import QueryResponse
from src.embeddings.embedder import Embedder, get_embedder

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    query: str
    query_vector: list[float]
    response: QueryResponse
    created_at: float
    hits: int = 0
    tenant_id: str = "default"


class SemanticCache:
    """
    Hybrid Redis and In-Memory semantic query cache.
    Caches queries and verified answers with tenant isolation and semantic similarity lookup.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.85,
        max_entries: int = 500,
        ttl_seconds: float = 3600.0,
        embedder: Embedder | None = None,
        redis_url: str | None = None,
    ) -> None:
        self.threshold = similarity_threshold
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self.embedder = embedder or get_embedder()
        self.entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self.total_lookups = 0
        self.total_hits = 0

        # Redis connection setup
        self._redis_client: Any = None
        self._redis_available = False
        target_redis = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

        try:
            import redis
            client = redis.from_url(target_redis, socket_connect_timeout=0.5, socket_timeout=0.5)
            client.ping()
            self._redis_client = client
            self._redis_available = True
            logger.info(f"Connected to Redis semantic cache at {target_redis}")
        except Exception as e:  # noqa: BLE001
            logger.info(f"Redis not available ({e}). Using in-memory LRU semantic cache.")

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two unit or raw vectors."""
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return sum(x * y for x, y in zip(a, b, strict=False)) / (norm_a * norm_b)

    def get(self, query: str, tenant_id: str = "default") -> QueryResponse | None:
        """
        Lookup response for query. First checks exact match, then semantic similarity.
        """
        clean_q = query.strip().lower()
        now = time.time()
        cache_key = f"{tenant_id}:{clean_q}"

        with self._lock:
            self.total_lookups += 1

            # 1. Exact string match (in-memory)
            if cache_key in self.entries:
                entry = self.entries[cache_key]
                if now - entry.created_at < self.ttl_seconds:
                    entry.hits += 1
                    self.total_hits += 1
                    self.entries.move_to_end(cache_key)
                    logger.info(f"Semantic Cache: Exact hit for '{clean_q[:30]}...'")
                    return entry.response
                del self.entries[cache_key]

        # 2. Redis exact match check
        if self._redis_available and self._redis_client is not None:
            try:
                raw_data = self._redis_client.get(f"rag_cache:{cache_key}")
                if raw_data:
                    data = json.loads(raw_data)
                    resp = QueryResponse(**data["response"])
                    with self._lock:
                        self.total_hits += 1
                    logger.info(f"Semantic Cache: Redis hit for '{clean_q[:30]}...'")
                    return resp
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Redis lookup error: {e}")

        # 3. Semantic similarity search over in-memory index
        query_vec = self.embedder.embed_query(query)
        best_score = -1.0
        best_key = None

        with self._lock:
            for key, entry in self.entries.items():
                if entry.tenant_id != tenant_id or (now - entry.created_at >= self.ttl_seconds):
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

    def put(self, query: str, response: QueryResponse, tenant_id: str = "default") -> None:
        """Store a verified query response in the semantic cache."""
        clean_q = query.strip().lower()
        now = time.time()
        cache_key = f"{tenant_id}:{clean_q}"
        query_vec = self.embedder.embed_query(query)

        with self._lock:
            # Enforce LRU capacity limit
            while len(self.entries) >= self.max_entries:
                self.entries.popitem(last=False)

            entry = CacheEntry(
                query=query,
                query_vector=query_vec,
                response=response,
                created_at=now,
                tenant_id=tenant_id,
            )
            self.entries[cache_key] = entry
            self.entries.move_to_end(cache_key)

        # Store in Redis if available
        if self._redis_available and self._redis_client is not None:
            try:
                payload = {
                    "query": query,
                    "query_vector": query_vec,
                    "response": response.model_dump(),
                    "created_at": now,
                    "tenant_id": tenant_id,
                }
                self._redis_client.setex(
                    f"rag_cache:{cache_key}",
                    int(self.ttl_seconds),
                    json.dumps(payload),
                )
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Redis cache setex failed: {e}")

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self.entries.clear()
            self.total_lookups = 0
            self.total_hits = 0

        if self._redis_available and self._redis_client is not None:
            try:
                for key in self._redis_client.scan_iter("rag_cache:*"):
                    self._redis_client.delete(key)
            except Exception as e:  # noqa: BLE001
                logger.debug(f"Redis cache clear failed: {e}")

    def stats(self) -> dict[str, Any]:
        """Return cache operational metrics."""
        with self._lock:
            hit_rate = (self.total_hits / self.total_lookups) if self.total_lookups > 0 else 0.0
            return {
                "entries_count": len(self.entries),
                "max_entries": self.max_entries,
                "total_lookups": self.total_lookups,
                "total_hits": self.total_hits,
                "hit_rate": round(hit_rate, 4),
                "redis_connected": self._redis_available,
            }
