"""
src/core/models.py — Core data models.

Every pipeline stage receives and returns these types.
This ensures type safety and makes data flow explicit.
"""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel, Field
import uuid


class QuestionType(str, Enum):
    DIRECT_LOOKUP = "direct_lookup"
    MULTI_HOP = "multi_hop"
    NUMERICAL = "numerical"
    DEFINITION = "definition"
    COMPARISON = "comparison"
    SUMMARIZATION = "summarization"
    CROSS_SECTION = "cross_section"
    CROSS_DOCUMENT = "cross_document"
    AMBIGUOUS = "ambiguous"
    UNANSWERABLE = "unanswerable"
    ADVERSARIAL = "adversarial"
    TABLE_BASED = "table_based"
    CONTRADICTORY = "contradictory"
    TEMPORAL = "temporal"
    LONG_CONTEXT = "long_context"


class SupportLevel(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class FailureCategory(str, Enum):
    RETRIEVAL = "retrieval_failure"
    CHUNKING = "chunking_failure"
    EMBEDDING = "embedding_failure"
    RANKING = "ranking_failure"
    CONTEXT_WINDOW = "context_window_failure"
    GENERATION = "generation_failure"
    CITATION = "citation_failure"
    HALLUCINATION = "hallucination"
    PARSING = "parsing_failure"
    OCR = "ocr_failure"
    TABLE_UNDERSTANDING = "table_understanding_failure"
    CONTRADICTORY_SOURCE = "contradictory_source_failure"
    UNANSWERABLE = "unanswerable_question_failure"
    LATENCY = "latency_failure"
    PROMPT_INJECTION = "prompt_injection_failure"


class QueryType(str, Enum):
    """Classified query type for adaptive retrieval."""
    EXACT = "exact"           # names, numbers, identifiers → lexical-heavy
    CONCEPTUAL = "conceptual" # abstract concepts → semantic-heavy
    TECHNICAL = "technical"   # domain-specific → balanced hybrid
    AMBIGUOUS = "ambiguous"   # unclear intent → expanded retrieval
    MULTI_HOP = "multi_hop"   # requires multiple passages → broader retrieval
    COMPARISON = "comparison" # compare entities → multi-document
    UNKNOWN = "unknown"       # default


# ── Document models ────────────────────────────────
class DocumentMetadata(BaseModel):
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    file_path: str
    file_size_bytes: int
    num_pages: int
    title: Optional[str] = None
    author: Optional[str] = None
    ingested_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    content_hash: str = ""


class TextChunk(BaseModel):
    chunk_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    content: str
    char_offset: int = 0
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddedChunk(TextChunk):
    embedding: list[float] = Field(default_factory=list)


# ── Retrieval models ───────────────────────────────
class RetrievalResult(BaseModel):
    chunk: TextChunk
    score: float
    retrieval_method: str
    rank: int


class RetrievalOutput(BaseModel):
    query: str
    candidates: list[RetrievalResult]
    total_candidates: int
    retrieval_latency_ms: float
    method_details: dict[str, Any] = Field(default_factory=dict)
    query_type: Optional[QueryType] = None
    adaptive_weights: Optional[dict[str, float]] = None


# ── Evidence models ────────────────────────────────
class EvidenceAssessment(BaseModel):
    """Assessment of whether retrieved evidence is sufficient."""
    is_sufficient: bool
    confidence: float              # 0.0 to 1.0
    evidence_score: float          # aggregate quality score
    coverage: float                # how much of the question is covered
    agreement: float               # do sources agree with each other?
    contradictions: list[dict] = Field(default_factory=list)
    recommendation: Literal["answer", "retrieve_more", "abstain"] = "answer"
    reasoning: str = ""


class Contradiction(BaseModel):
    """A detected contradiction between sources."""
    claim_a: str
    claim_b: str
    source_a: str
    source_b: str
    page_a: int
    page_b: int
    severity: Literal["minor", "major", "critical"] = "major"


# ── Generation models ──────────────────────────────
class Citation(BaseModel):
    citation_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    document_id: str
    filename: str
    page_number: int
    section: Optional[str] = None
    chunk_id: str
    relevant_text: str
    validated: bool = False


class GenerationOutput(BaseModel):
    answer: str
    support_level: SupportLevel
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    generation_latency_ms: float = 0.0
    token_usage: dict[str, int] = Field(default_factory=dict)
    abstained: bool = False


class QueryResponse(BaseModel):
    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    answer: str
    support_level: SupportLevel
    confidence: float
    citations: list[Citation] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    retrieval_metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_assessment: Optional[EvidenceAssessment] = None
    latency: dict[str, float] = Field(default_factory=dict)
    token_usage: dict[str, int] = Field(default_factory=dict)
    abstained: bool = False


# ── Evaluation models ──────────────────────────────
class BenchmarkQuestion(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    question: str
    expected_answer: str
    source_document: str
    source_page: Optional[int] = None
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    question_type: QuestionType = QuestionType.DIRECT_LOOKUP
    difficulty: int = 1
    answerable: bool = True
    notes: Optional[str] = None


class EvaluationResult(BaseModel):
    question_id: str
    question: str
    expected_answer: str
    generated_answer: str
    support_level: SupportLevel
    retrieved_correct_source: bool = False
    retrieved_correct_passage: bool = False
    recall_at_k: dict[str, float] = Field(default_factory=dict)
    factual_correctness: float = 0.0
    groundedness: float = 0.0
    citation_accuracy: float = 0.0
    hallucination_detected: bool = False
    latency_ms: float = 0.0
    failure_category: Optional[FailureCategory] = None
    failure_notes: Optional[str] = None


class ExperimentResult(BaseModel):
    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    hypothesis: str
    method: str
    config_snapshot: dict[str, Any]
    dataset_version: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metrics: dict[str, float] = Field(default_factory=dict)
    question_results: list[EvaluationResult] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    errors: list[str] = Field(default_factory=list)
    interpretation: str = ""
    limitations: str = ""
    next_experiment: str = ""
