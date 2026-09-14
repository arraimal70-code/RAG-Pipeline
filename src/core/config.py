"""
Production-ready configuration management with validation and environment support.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Literal
from dataclasses import dataclass, field
from pydantic import BaseModel, validator
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ConfigValidationError(Exception):
    """Raised when configuration validation fails."""
    pass


@dataclass
class ChunkingConfig:
    """Configuration for document chunking."""
    strategy: Literal["fixed", "sentence", "recursive", "structure"] = "recursive"
    chunk_size: int = 512
    chunk_overlap: int = 64
    min_chunk_size: int = 50
    max_chunk_size: int = 1024
    separators: list[str] = field(default_factory=lambda: ["\n\n", "\n", ". ", " ", ""])
    
    @validator('chunk_overlap')
    def validate_overlap(cls, v, values):
        if 'chunk_size' in values and v >= values['chunk_size']:
            raise ValueError('chunk_overlap must be less than chunk_size')
        return v


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    provider: Literal["local", "openai"] = "local"
    model_name: str = "all-MiniLM-L6-v2"
    dimension: int = 384
    batch_size: int = 64
    normalize: bool = True


@dataclass
class RetrievalConfig:
    """Configuration for retrieval system."""
    dense_top_k: int = 50
    bm25_top_k: int = 50
    fusion_method: Literal["rrf", "weighted", "interleave"] = "rrf"
    rrf_k: int = 60
    dense_weight: float = 0.6
    bm25_weight: float = 0.4
    post_fusion_top_k: int = 20
    rerank_enabled: bool = True
    rerank_top_k: int = 5
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    adaptive_enabled: bool = True
    adaptive_strategy: Literal["query_type", "confidence", "hybrid"] = "query_type"
    
    @validator('dense_weight')
    def validate_weights(cls, v, values):
        if 'bm25_weight' in values:
            total = v + values['bm25_weight']
            if abs(total - 1.0) > 0.01:
                raise ValueError(f'dense_weight + bm25_weight must equal 1.0, got {total}')
        return v


@dataclass
class GenerationConfig:
    """Configuration for LLM generation."""
    provider: Literal["openai"] = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 1024
    abstention_threshold: float = 0.5


@dataclass
class EvidenceConfig:
    """Configuration for evidence assessment."""
    sufficiency_enabled: bool = True
    min_evidence_score: float = 0.3
    contradiction_threshold: float = 0.7
    max_retrieval_attempts: int = 2


@dataclass
class SecurityConfig:
    """Configuration for security settings."""
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
class MonitoringConfig:
    """Configuration for monitoring and observability."""
    enable_tracing: bool = True
    enable_metrics: bool = True
    log_level: str = "INFO"
    trace_log_dir: str = "logs/traces"
    metrics_log_dir: str = "logs/metrics"


@dataclass
class PerformanceConfig:
    """Configuration for performance settings."""
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    max_concurrent_queries: int = 10
    query_timeout_seconds: int = 30
    enable_batching: bool = True
    batch_size: int = 32


@dataclass
class AppConfig:
    """Main application configuration."""
    chunking: ChunkingConfig = field(default_factory=ChunkingConfig)
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Environment variables
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    
    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"
    
    @property
    def documents_dir(self) -> Path:
        return self.data_dir / "documents"
    
    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma_db"
    
    @property
    def bm25_index_dir(self) -> Path:
        return self.data_dir / "bm25_index"
    
    @property
    def experiments_dir(self) -> Path:
        return self.base_dir / "experiments" / "results"
    
    @property
    def eval_dir(self) -> Path:
        return self.base_dir / "benchmarks"
    
    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"
    
    def validate(self) -> None:
        """Validate configuration and create necessary directories."""
        # Validate API key
        if not self.openai_api_key and self.generation.provider == "openai":
            logger.warning(
                "OPENAI_API_KEY not set. LLM generation will fail. "
                "Set it in .env file or environment variables."
            )
        
        # Validate weights
        if abs(self.retrieval.dense_weight + self.retrieval.bm25_weight - 1.0) > 0.01:
            raise ConfigValidationError(
                f"dense_weight ({self.retrieval.dense_weight}) + "
                f"bm25_weight ({self.retrieval.bm25_weight}) must equal 1.0"
            )
        
        # Validate chunking
        if self.chunking.chunk_overlap >= self.chunking.chunk_size:
            raise ConfigValidationError(
                f"chunk_overlap ({self.chunking.chunk_overlap}) must be less than "
                f"chunk_size ({self.chunking.chunk_size})"
            )
        
        # Validate reranking
        if self.retrieval.rerank_top_k > self.retrieval.post_fusion_top_k:
            raise ConfigValidationError(
                f"rerank_top_k ({self.retrieval.rerank_top_k}) must be <= "
                f"post_fusion_top_k ({self.retrieval.post_fusion_top_k})"
            )
        
        # Create directories
        for dir_path in [
            self.documents_dir,
            self.chroma_dir,
            self.bm25_index_dir,
            self.experiments_dir,
            self.eval_dir,
            self.logs_dir,
            Path(self.monitoring.trace_log_dir),
            Path(self.monitoring.metrics_log_dir),
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        logger.info("Configuration validated successfully")
    
    def to_dict(self) -> dict:
        """Convert configuration to dictionary for serialization."""
        return {
            "chunking": {
                "strategy": self.chunking.strategy,
                "chunk_size": self.chunking.chunk_size,
                "chunk_overlap": self.chunking.chunk_overlap,
            },
            "embedding": {
                "provider": self.embedding.provider,
                "model_name": self.embedding.model_name,
            },
            "retrieval": {
                "dense_top_k": self.retrieval.dense_top_k,
                "bm25_top_k": self.retrieval.bm25_top_k,
                "fusion_method": self.retrieval.fusion_method,
                "dense_weight": self.retrieval.dense_weight,
                "bm25_weight": self.retrieval.bm25_weight,
                "rerank_enabled": self.retrieval.rerank_enabled,
                "adaptive_enabled": self.retrieval.adaptive_enabled,
            },
            "generation": {
                "model": self.generation.model,
                "temperature": self.generation.temperature,
            },
            "evidence": {
                "sufficiency_enabled": self.evidence.sufficiency_enabled,
                "min_evidence_score": self.evidence.min_evidence_score,
            },
            "security": {
                "max_file_size_mb": self.security.max_file_size_mb,
                "max_pages_per_document": self.security.max_pages_per_document,
            },
            "monitoring": {
                "enable_tracing": self.monitoring.enable_tracing,
                "enable_metrics": self.monitoring.enable_metrics,
            },
            "performance": {
                "enable_caching": self.performance.enable_caching,
                "max_concurrent_queries": self.performance.max_concurrent_queries,
            },
        }


# Global configuration instance
try:
    config = AppConfig()
    config.validate()
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    raise
