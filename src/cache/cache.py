"""
Production-grade caching layer for RAG Pipeline performance optimization.
"""

import time
import logging
import hashlib
import json
from pathlib import Path
from typing import Optional, Any, Dict, Callable
from datetime import datetime, timedelta
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with metadata."""
    
    def __init__(self, key: str, value: Any, ttl_seconds: int):
        self.key = key
        self.value = value
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(seconds=ttl_seconds)
        self.access_count = 0
        self.last_accessed = self.created_at
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.utcnow() > self.expires_at
    
    def access(self) -> Any:
        """Access the cached value."""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()
        return self.value


class Cache:
    """
    Thread-safe in-memory cache with TTL support.
    
    Features:
    - TTL-based expiration
    - Thread-safe operations
    - Cache statistics
    - Manual invalidation
    - Size limits
    """
    
    def __init__(
        self,
        max_size: int = 10000,
        default_ttl_seconds: int = 3600,
        name: str = "default",
    ):
        self.max_size = max_size
        self.default_ttl = default_ttl_seconds
        self.name = name
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        
        logger.info(f"Cache '{name}' initialized (max_size={max_size}, ttl={default_ttl_seconds}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return None
            
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None
            
            self._hits += 1
            return entry.access()
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set value in cache."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheEntry(key, value, ttl)
    
    def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            logger.info(f"Cache '{self.name}' cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0
            
            return {
                "name": self.name,
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": hit_rate,
                "evictions": self._evictions,
            }
    
    def _evict_oldest(self) -> None:
        """Evict oldest entry (LRU-like behavior)."""
        if not self._cache:
            return
        
        # Find entry with oldest last_accessed time
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].last_accessed
        )
        
        del self._cache[oldest_key]
        self._evictions += 1
        logger.debug(f"Evicted cache entry: {oldest_key}")
    
    def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._cache[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
            
            return len(expired_keys)


class QueryCache:
    """
    Specialized cache for query results.
    
    Provides:
    - Query-specific caching
    - Automatic key generation
    - Result validation
    - Cache invalidation by document
    """
    
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache or Cache(
            max_size=5000,
            default_ttl_seconds=3600,
            name="query_cache",
        )
    
    def _generate_key(self, query: str, config_hash: str) -> str:
        """Generate cache key from query and configuration."""
        # Normalize query
        normalized = query.strip().lower()
        
        # Create hash
        key_data = f"{normalized}:{config_hash}"
        key_hash = hashlib.sha256(key_data.encode()).hexdigest()[:16]
        
        return f"query:{key_hash}"
    
    def get(self, query: str, config_hash: str) -> Optional[Any]:
        """Get cached query result."""
        key = self._generate_key(query, config_hash)
        return self.cache.get(key)
    
    def set(self, query: str, config_hash: str, result: Any, ttl_seconds: Optional[int] = None) -> None:
        """Cache query result."""
        key = self._generate_key(query, config_hash)
        self.cache.set(key, result, ttl_seconds)
    
    def invalidate_by_document(self, document_id: str) -> int:
        """
        Invalidate cache entries related to a document.
        
        Note: This is a simplified implementation. In production,
        you'd want to track which queries depend on which documents.
        """
        # For now, clear entire cache
        # In production, maintain a document->query mapping
        logger.warning(
            f"Document {document_id} changed, clearing query cache. "
            "Consider implementing document-specific invalidation."
        )
        self.cache.clear()
        return 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


class EmbeddingCache:
    """
    Cache for embedding vectors to avoid re-computation.
    """
    
    def __init__(self, cache: Optional[Cache] = None):
        self.cache = cache or Cache(
            max_size=100000,
            default_ttl_seconds=86400,  # 24 hours
            name="embedding_cache",
        )
    
    def _generate_key(self, text: str, model_name: str) -> str:
        """Generate cache key for embedding."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"embedding:{model_name}:{text_hash}"
    
    def get(self, text: str, model_name: str) -> Optional[list]:
        """Get cached embedding."""
        key = self._generate_key(text, model_name)
        return self.cache.get(key)
    
    def set(self, text: str, model_name: str, embedding: list, ttl_seconds: Optional[int] = None) -> None:
        """Cache embedding."""
        key = self._generate_key(text, model_name)
        self.cache.set(key, embedding, ttl_seconds)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self.cache.get_stats()


def cached_query(ttl_seconds: int = 3600):
    """
    Decorator to cache query results.
    
    Usage:
        @cached_query(ttl_seconds=3600)
        def query(self, question: str):
            # ... query logic
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, question: str, *args, **kwargs):
            # Check if caching is enabled
            if not hasattr(self, 'query_cache'):
                logger.warning("Query cache not available, skipping cache")
                return func(self, question, *args, **kwargs)
            
            # Generate config hash
            config_hash = hashlib.sha256(
                json.dumps(kwargs, sort_keys=True).encode()
            ).hexdigest()[:8]
            
            # Try to get from cache
            cached_result = self.query_cache.get(question, config_hash)
            if cached_result is not None:
                logger.debug(f"Cache hit for query: {question[:50]}...")
                return cached_result
            
            # Execute query
            logger.debug(f"Cache miss for query: {question[:50]}...")
            result = func(self, question, *args, **kwargs)
            
            # Cache result
            self.query_cache.set(question, config_hash, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


# Global cache instances
query_cache = QueryCache()
embedding_cache = EmbeddingCache()


def get_query_cache() -> QueryCache:
    """Get the global query cache."""
    return query_cache


def get_embedding_cache() -> EmbeddingCache:
    """Get the global embedding cache."""
    return embedding_cache


def cleanup_all_caches() -> Dict[str, int]:
    """Clean up all expired cache entries."""
    return {
        "query_cache": query_cache.cache.cleanup_expired(),
        "embedding_cache": embedding_cache.cache.cleanup_expired(),
    }
