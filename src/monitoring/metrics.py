"""
Production-grade monitoring and metrics collection for RAG Pipeline.
"""

import time
import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import threading

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric measurement."""
    timestamp: str
    value: float
    tags: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    query_id: str
    timestamp: str
    query_text: str
    query_type: str
    latency_ms: float
    retrieval_latency_ms: float
    generation_latency_ms: float
    num_candidates: int
    num_citations: int
    confidence: float
    support_level: str
    abstained: bool
    token_usage: Dict[str, int] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """
    Thread-safe metrics collection and aggregation.
    
    Collects:
    - Query latencies
    - Error rates
    - Token usage
    - Retrieval metrics
    - System health
    """
    
    def __init__(self, log_dir: str = "logs/metrics"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Thread-safe storage
        self._lock = threading.Lock()
        self._query_metrics: List[QueryMetrics] = []
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        
        # Rolling window for recent metrics (last hour)
        self._window_size = timedelta(hours=1)
        
        logger.info(f"MetricsCollector initialized, logging to {log_dir}")
    
    def record_query(self, metrics: QueryMetrics) -> None:
        """Record metrics for a query."""
        with self._lock:
            self._query_metrics.append(metrics)
            
            # Update counters
            self._counters["total_queries"] += 1
            if metrics.error:
                self._counters["total_errors"] += 1
            if metrics.abstained:
                self._counters["total_abstentions"] += 1
            
            # Update histograms
            self._histograms["query_latency_ms"].append(metrics.latency_ms)
            self._histograms["retrieval_latency_ms"].append(metrics.retrieval_latency_ms)
            self._histograms["generation_latency_ms"].append(metrics.generation_latency_ms)
            self._histograms["num_candidates"].append(metrics.num_candidates)
            self._histograms["num_citations"].append(metrics.num_citations)
            self._histograms["confidence"].append(metrics.confidence)
            
            # Update token usage
            for key, value in metrics.token_usage.items():
                self._counters[f"tokens_{key}"] += value
        
        # Log to file
        self._log_query(metrics)
    
    def record_counter(self, name: str, value: int = 1) -> None:
        """Record a counter metric."""
        with self._lock:
            self._counters[name] += value
    
    def record_gauge(self, name: str, value: float) -> None:
        """Record a gauge metric."""
        with self._lock:
            self._gauges[name] = value
    
    def record_histogram(self, name: str, value: float) -> None:
        """Record a histogram metric."""
        with self._lock:
            self._histograms[name].append(value)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        with self._lock:
            now = datetime.utcnow()
            cutoff = now - self._window_size
            
            # Filter recent queries
            recent_queries = [
                q for q in self._query_metrics
                if datetime.fromisoformat(q.timestamp) > cutoff
            ]
            
            summary = {
                "timestamp": now.isoformat(),
                "window_hours": 1,
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "recent_queries": len(recent_queries),
            }
            
            # Calculate histogram statistics
            for name, values in self._histograms.items():
                if values:
                    recent_values = [
                        v for v, q in zip(values, self._query_metrics)
                        if datetime.fromisoformat(q.timestamp) > cutoff
                    ]
                    if recent_values:
                        summary[f"{name}_mean"] = sum(recent_values) / len(recent_values)
                        summary[f"{name}_min"] = min(recent_values)
                        summary[f"{name}_max"] = max(recent_values)
                        sorted_values = sorted(recent_values)
                        p50_idx = len(sorted_values) // 2
                        p95_idx = int(len(sorted_values) * 0.95)
                        summary[f"{name}_p50"] = sorted_values[p50_idx]
                        summary[f"{name}_p95"] = sorted_values[min(p95_idx, len(sorted_values) - 1)]
            
            # Calculate error rate
            if self._counters["total_queries"] > 0:
                summary["error_rate"] = (
                    self._counters["total_errors"] / self._counters["total_queries"]
                )
            
            return summary
    
    def get_query_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent query metrics."""
        with self._lock:
            return [q.to_dict() for q in self._query_metrics[-limit:]]
    
    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._query_metrics.clear()
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
        logger.info("Metrics reset")
    
    def _log_query(self, metrics: QueryMetrics) -> None:
        """Log query metrics to file."""
        try:
            timestamp = datetime.utcnow().strftime("%Y%m%d")
            log_file = self.log_dir / f"queries_{timestamp}.jsonl"
            
            with open(log_file, "a") as f:
                f.write(json.dumps(metrics.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to log query metrics: {e}")
    
    def export_to_json(self, filepath: str) -> None:
        """Export all metrics to JSON file."""
        with self._lock:
            data = {
                "summary": self.get_summary(),
                "query_metrics": [q.to_dict() for q in self._query_metrics],
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: list(v) for k, v in self._histograms.items()},
            }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Metrics exported to {filepath}")


class HealthChecker:
    """
    System health checking and monitoring.
    
    Checks:
    - Component initialization
    - Index availability
    - API connectivity
    - Resource usage
    - Error rates
    """
    
    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.checks: Dict[str, callable] = {
            "vector_index": self._check_vector_index,
            "bm25_index": self._check_bm25_index,
            "embedder": self._check_embedder,
            "generator": self._check_generator,
            "error_rate": self._check_error_rate,
        }
    
    def check_all(self) -> Dict[str, Any]:
        """Run all health checks."""
        results = {}
        all_healthy = True
        
        for name, check_func in self.checks.items():
            try:
                result = check_func()
                results[name] = result
                if not result.get("healthy", False):
                    all_healthy = False
            except Exception as e:
                results[name] = {
                    "healthy": False,
                    "error": str(e),
                }
                all_healthy = False
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": results,
        }
    
    def _check_vector_index(self) -> Dict[str, Any]:
        """Check vector index health."""
        try:
            count = self.pipeline.vector_index.count()
            return {
                "healthy": True,
                "count": count,
                "message": f"Vector index has {count} chunks",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }
    
    def _check_bm25_index(self) -> Dict[str, Any]:
        """Check BM25 index health."""
        try:
            count = self.pipeline.bm25_index.count()
            return {
                "healthy": True,
                "count": count,
                "message": f"BM25 index has {count} chunks",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }
    
    def _check_embedder(self) -> Dict[str, Any]:
        """Check embedder health."""
        try:
            # Test embedding a simple text
            test_embedding = self.pipeline.embedder.embed_query("test")
            return {
                "healthy": True,
                "dimension": len(test_embedding),
                "message": "Embedder is functional",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }
    
    def _check_generator(self) -> Dict[str, Any]:
        """Check generator health."""
        try:
            # Just check if generator is initialized
            if self.pipeline.generator and self.pipeline.generator.llm:
                return {
                    "healthy": True,
                    "model": self.pipeline.generator.llm.model_name,
                    "message": "Generator is initialized",
                }
            else:
                return {
                    "healthy": False,
                    "error": "Generator not initialized",
                }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }
    
    def _check_error_rate(self) -> Dict[str, Any]:
        """Check error rate."""
        try:
            health = self.pipeline.get_health_status()
            error_rate = health.get("error_rate", 0.0)
            
            # Threshold: 5% error rate is unhealthy
            healthy = error_rate < 0.05
            
            return {
                "healthy": healthy,
                "error_rate": error_rate,
                "threshold": 0.05,
                "message": f"Error rate: {error_rate:.2%}",
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
            }


# Global metrics collector
metrics_collector = MetricsCollector()


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector."""
    return metrics_collector


def get_health_checker(pipeline) -> HealthChecker:
    """Get a health checker for the pipeline."""
    return HealthChecker(pipeline)
