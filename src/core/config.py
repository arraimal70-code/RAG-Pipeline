"""
src/core/config.py — Central configuration management.

All tunable parameters live here. Configuration is validated at import
time. Experiments can override any parameter without modifying this file.
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Literal
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma_db"
BM25_INDEX_DIR = DATA_DIR / "bm25_index"
EXPERIMENTS_DIR = BASE_DIR / "experiments" / "results"
EVAL_DIR = BASE_DIR / "benchmarks"
LOGS_DIR = BASE_DIR / "logs"

for d in [DOCUMENTS_DIR, CHROMA_DIR, BM25_INDEX_DIR, EXPERIMENTS_DIR, EVAL_DIR, LOGS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


@dataclass
class ChunkingConfig:
    strategy: Literal["fixed", "sentence", "recursive", "structure"] = "recursive"
    chunk_size: int = 512          # tokens (approx chars/4)
    chunk_overlap: int = 64
    min_chunk_size: int = 50
    max_chunk_size: int = 1024
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])


@dataclass
class EmbeddingConfig:
    provider: Literal["local", "openai"] = "local"
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 64
    normalize: bool = True


@dataclass
class RetrievalConfig:
    # Candidate generation
    dense_top_k: int = 50
    bm25_top_k: int = 50
    # Fusion
    fusion_method: Literal["rrf", "weighted", "interleave"] = "rrf"
    rrf_k: int = 60
    dense_weight: float = 0.6
    bm25_weight: float = 0.4
    # Post-fusion
    post_fusion_top_k: int = 20
    # Reranking
    rerank_enabled: bool = True
    rerank_top_k: int = 5
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    # Adaptive retrieval
    adaptive_enabled: bool = True
    adaptive_strategy: Literal["query_type", "confidence", "hybrid"] = "query_type"


@dataclass
class GenerationConfig:
    provider: Literal["openai"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 1024
    abstention_threshold: float = 0.5


@dataclass
class EvidenceConfig:
    """Evidence sufficiency and contradiction detection."""
    sufficiency_enabled: bool = True
    min_evidence_score: float = 0.3
    contradiction_threshold: float = 0.7
    max_retrieval_attempts: int = 2  # adaptive: retrieve again if insufficient


@dataclass
class SecurityConfig:
    max_file_size_mb: int = 50
    max_pages_per_document: int = 500
    max_chunk_length: int = 10000
    allowed_extensions: list[str] = field(default_factory=lambda: [".pdf"])
    sanitize_retrieved_text: bool = True
    injection_patterns: list[str] = field(default_factory=lambda: [
        "ignore previous instructions",
        "ignore all previous",
        "you are now",
        "disregard your",
        "new instructions:",
    ])


@dataclass
class AppConfig:
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    def validate(self) -> None:
        if not self.openai_api_key and self.generation.provider == "openai":
            logger.warning("OPENAI_API_KEY not set. LLM generation will fail.")
        if self.chunking.chunk_overlap >= self.chunking.chunk_size:
            raise ValueError("chunk_overlap must be < chunk_size")
        if self.retrieval.rerank_top_k > self.retrieval.post_fusion_top_k:
            raise ValueError("rerank_top_k must be <= post_fusion_top_k")
        if abs(self.retrieval.dense_weight + self.retrieval.bm25_weight - 1.0) > 0.01:
            raise ValueError("dense_weight + bm25_weight must equal 1.0")


config = AppConfig()
config.validate()
