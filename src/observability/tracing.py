"""
src/observability/tracing.py — Query tracing and observability.

Every query produces a trace that records:
- Query text and classification
- Retrieval strategy and weights used
- Retrieved documents and scores
- Reranking results
- Evidence sufficiency assessment
- Decision (answer / retrieve_more / abstain)
- Generation latency
- Citation validation results
- Final answer

This makes debugging possible and provides data for analysis.

WHY: Without tracing, you can't understand WHY the system made
a particular decision. Tracing turns a black box into a debuggable
system.
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from src.core.config import config

logger = logging.getLogger(__name__)


@dataclass
class TraceEvent:
    """A single event in a query trace."""
    timestamp: str
    stage: str
    data: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0


@dataclass
class QueryTrace:
    """Complete trace for a single query."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    query_type: str = "unknown"
    events: list[TraceEvent] = field(default_factory=list)
    total_latency_ms: float = 0.0
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    def add_event(self, stage: str, data: dict, latency_ms: float = 0.0) -> None:
        """Add an event to the trace."""
        event = TraceEvent(
            timestamp=datetime.utcnow().isoformat(),
            stage=stage,
            data=data,
            latency_ms=latency_ms,
        )
        self.events.append(event)

    def to_dict(self) -> dict:
        """Convert trace to dictionary for serialization."""
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "query_type": self.query_type,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_latency_ms": self.total_latency_ms,
            "events": [asdict(e) for e in self.events],
        }

    def to_json(self) -> str:
        """Serialize trace to JSON."""
        return json.dumps(self.to_dict(), indent=2, default=str)


class Tracer:
    """
    Manages query traces.

    Usage:
        tracer = Tracer()
        trace = tracer.start_trace("What was revenue in FY2024?")
        trace.add_event("query_analysis", {"type": "numerical"})
        trace.add_event("retrieval", {"candidates": 50}, latency_ms=45.0)
        trace.add_event("reranking", {"candidates": 5}, latency_ms=50.0)
        trace.add_event("evidence_check", {"sufficient": True})
        trace.add_event("generation", {"abstained": False}, latency_ms=120.0)
        tracer.end_trace(trace)
        tracer.save_trace(trace)
    """

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = log_dir or config.LOGS_DIR
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._traces: list[QueryTrace] = []

    def start_trace(self, query: str) -> QueryTrace:
        """Start a new trace for a query."""
        trace = QueryTrace(
            query=query,
            start_time=datetime.utcnow().isoformat(),
        )
        logger.debug(f"Started trace {trace.trace_id} for query: {query[:50]}...")
        return trace

    def end_trace(self, trace: QueryTrace) -> None:
        """End a trace and compute total latency."""
        trace.end_time = datetime.utcnow().isoformat()

        if trace.start_time and trace.end_time:
            start = datetime.fromisoformat(trace.start_time)
            end = datetime.fromisoformat(trace.end_time)
            trace.total_latency_ms = (end - start).total_seconds() * 1000

        self._traces.append(trace)
        logger.debug(
            f"Ended trace {trace.trace_id}: "
            f"{len(trace.events)} events, "
            f"{trace.total_latency_ms:.0f}ms total"
        )

    def save_trace(self, trace: QueryTrace) -> Path:
        """Save a trace to disk as JSON."""
        filename = f"trace_{trace.trace_id[:8]}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.log_dir / filename

        with open(filepath, "w") as f:
            f.write(trace.to_json())

        logger.debug(f"Saved trace to {filepath}")
        return filepath

    def get_recent_traces(self, n: int = 10) -> list[QueryTrace]:
        """Get the most recent traces."""
        return self._traces[-n:]

    def get_trace_summary(self) -> dict:
        """Get a summary of all traces."""
        if not self._traces:
            return {"total_traces": 0}

        latencies = [t.total_latency_ms for t in self._traces if t.total_latency_ms > 0]
        query_types = {}
        for t in self._traces:
            qt = t.query_type
            query_types[qt] = query_types.get(qt, 0) + 1

        return {
            "total_traces": len(self._traces),
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p50_latency_ms": sorted(latencies)[len(latencies) // 2] if latencies else 0,
            "p95_latency_ms": sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0,
            "query_type_distribution": query_types,
        }


# Global tracer instance
tracer = Tracer()
