"""
Production-ready RAG Pipeline with comprehensive error handling, monitoring, and validation.
"""

import time
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from contextlib import contextmanager

from src.core.config import config
from src.core.models import QueryResponse, TextChunk, EmbeddedChunk
from src.parsing.pdf_parser import PDFParser
from src.chunking.chunker import get_chunker
from src.embeddings.embedder import get_embedder
from src.indexing.vector_store import VectorIndex
from src.indexing.bm25_index import BM25Index
from src.adaptive.query_analyzer import QueryAnalyzer
from src.adaptive.policy import policy_generator
from src.retrieval.hybrid_retriever import HybridRetriever
from src.reasoning.numerical import NumericalReasoner
from src.reasoning.temporal import TemporalReasoner
from src.evidence.sufficiency import EvidenceSufficiencyChecker
from src.generation.generator import Generator
from src.citations.validator import CitationValidator
from src.claims.extractor import ClaimExtractor
from src.observability.tracing import tracer
from src.security.validator import DocumentValidator, QueryValidator

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class DocumentIngestionError(PipelineError):
    """Error during document ingestion."""
    pass


class QueryProcessingError(PipelineError):
    """Error during query processing."""
    pass


class RetrievalError(PipelineError):
    """Error during retrieval."""
    pass


class GenerationError(PipelineError):
    """Error during generation."""
    pass


class RAGPipeline:
    """
    Production-ready RAG Pipeline with comprehensive monitoring and validation.
    
    Features:
    - Adaptive retrieval with query-type-aware policies
    - Evidence sufficiency assessment
    - Citation validation
    - Numerical and temporal reasoning
    - Comprehensive error handling
    - Performance monitoring
    - Security validation
    """
    
    def __init__(self):
        """Initialize pipeline with all components."""
        logger.info("Initializing RAG Pipeline...")
        
        # Core components
        self.parser = PDFParser()
        self.embedder = get_embedder()
        self.vector_index = VectorIndex()
        self.bm25_index = BM25Index()
        
        # Adaptive retrieval
        self.query_analyzer = QueryAnalyzer()
        self.retriever = HybridRetriever()
        
        # Reasoning
        self.numerical_reasoner = NumericalReasoner()
        self.temporal_reasoner = TemporalReasoner()
        
        # Evidence and validation
        self.evidence_checker = EvidenceSufficiencyChecker()
        self.generator = Generator()
        self.citation_validator = CitationValidator()
        self.claim_extractor = ClaimExtractor()
        
        # Security
        self.document_validator = DocumentValidator()
        self.query_validator = QueryValidator()
        
        # Monitoring
        self.query_count = 0
        self.error_count = 0
        self.start_time = datetime.utcnow()
        
        logger.info("RAG Pipeline initialized successfully")
    
    @contextmanager
    def _track_performance(self, operation: str):
        """Context manager to track operation performance."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - start) * 1000
            logger.debug(f"{operation} completed in {elapsed:.2f}ms")
    
    def ingest_document(self, file_path: str) -> Dict[str, Any]:
        """
        Ingest a document into the system with comprehensive validation.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Dictionary with ingestion metadata
            
        Raises:
            DocumentIngestionError: If ingestion fails
        """
        path = Path(file_path)
        
        with self._track_performance("document_ingestion"):
            try:
                # Validate document
                logger.info(f"Validating document: {path.name}")
                is_valid, reason = self.document_validator.validate(path)
                if not is_valid:
                    raise DocumentIngestionError(f"Document validation failed: {reason}")
                
                # Parse document
                logger.info(f"Parsing document: {path.name}")
                metadata, page_chunks = self.parser.parse(path)
                
                # Chunk document
                logger.info(f"Chunking document with strategy: {config.chunking.strategy}")
                chunker = get_chunker(config.chunking.strategy)
                chunks = chunker.chunk(page_chunks, config.chunking)
                
                if not chunks:
                    raise DocumentIngestionError("No chunks generated from document")
                
                # Generate embeddings
                logger.info(f"Generating embeddings for {len(chunks)} chunks")
                texts = [c.content for c in chunks]
                embeddings = self.embedder.embed(texts)
                
                # Create embedded chunks
                embedded_chunks = [
                    EmbeddedChunk(**c.model_dump(), embedding=e)
                    for c, e in zip(chunks, embeddings)
                ]
                
                # Store in vector index
                logger.info("Storing chunks in vector index")
                self.vector_index.add_chunks(embedded_chunks)
                
                # Build BM25 index
                logger.info("Building BM25 index")
                self.bm25_index.build(chunks)
                
                result = {
                    "document_id": metadata.document_id,
                    "filename": metadata.filename,
                    "num_pages": metadata.num_pages,
                    "num_chunks": len(chunks),
                    "status": "success",
                }
                
                logger.info(f"Successfully ingested {path.name}: {len(chunks)} chunks")
                return result
                
            except Exception as e:
                logger.error(f"Failed to ingest document {path.name}: {e}")
                self.error_count += 1
                raise DocumentIngestionError(f"Document ingestion failed: {e}") from e
    
    def query(self, question: str) -> QueryResponse:
        """
        Process a query through the full pipeline with comprehensive validation.
        
        Args:
            question: The question to answer
            
        Returns:
            QueryResponse with answer, citations, and metadata
            
        Raises:
            QueryProcessingError: If query processing fails
        """
        query_id = f"query_{self.query_count}_{int(time.time())}"
        self.query_count += 1
        
        with self._track_performance("query_processing"):
            try:
                # Start trace
                trace = tracer.start_trace(question)
                
                # Validate query
                logger.info(f"Validating query: {question[:50]}...")
                is_safe, reason = self.query_validator.validate(question)
                if not is_safe:
                    logger.warning(f"Query validation failed: {reason}")
                    # Sanitize query
                    question = self.query_validator.sanitize(question)
                
                # Stage 1: Query analysis
                logger.info("Analyzing query type")
                query_type = self.query_analyzer.classify(question)
                trace.add_event("query_analysis", {
                    "query_type": query_type.value,
                })
                
                # Stage 2: Generate retrieval policy
                logger.info(f"Generating retrieval policy for {query_type.value}")
                policy = policy_generator.generate_policy(query_type, question)
                trace.add_event("policy_generation", {
                    "policy": policy.to_dict(),
                })
                
                # Stage 3: Retrieval
                logger.info("Retrieving relevant chunks")
                retrieval = self.retriever.retrieve(question, policy=policy)
                trace.add_event("retrieval", {
                    "num_candidates": retrieval.total_candidates,
                    "method_details": retrieval.method_details,
                })
                
                if not retrieval.candidates:
                    logger.warning("No candidates retrieved")
                    return QueryResponse(
                        question=question,
                        answer="No relevant documents found.",
                        support_level="insufficient_evidence",
                        confidence=0.0,
                        citations=[],
                        abstained=True,
                    )
                
                # Stage 4: Temporal filtering
                logger.info("Applying temporal filtering")
                retrieval = self.temporal_reasoner.filter_by_temporal_relevance(
                    question, retrieval
                )
                
                # Stage 5: Evidence sufficiency assessment
                logger.info("Assessing evidence sufficiency")
                evidence_assessment = self.evidence_checker.assess(question, retrieval)
                trace.add_event("evidence_assessment", {
                    "is_sufficient": evidence_assessment.is_sufficient,
                    "confidence": evidence_assessment.confidence,
                    "recommendation": evidence_assessment.recommendation,
                })
                
                # Check if we should abstain
                if evidence_assessment.recommendation == "abstain":
                    logger.info("Evidence insufficient, abstaining")
                    return QueryResponse(
                        question=question,
                        answer="I don't have sufficient evidence to answer this question reliably.",
                        support_level="insufficient_evidence",
                        confidence=0.0,
                        citations=[],
                        abstained=True,
                    )
                
                # Stage 6: Numerical reasoning (if applicable)
                numerical_result = None
                if query_type.value in ["numerical", "calculation", "comparison"]:
                    logger.info("Applying numerical reasoning")
                    numerical_result = self.numerical_reasoner.reason_about_question(
                        question, [c.chunk for c in retrieval.candidates]
                    )
                
                # Stage 7: Generation
                logger.info("Generating answer")
                generation = self.generator.generate(question, retrieval)
                trace.add_event("generation", {
                    "support_level": generation.support_level.value,
                    "confidence": generation.confidence,
                    "num_citations": len(generation.citations),
                })
                
                # Stage 8: Citation validation
                logger.info("Validating citations")
                generation = self.citation_validator.validate_citations(generation, retrieval)
                citation_metrics = self.citation_validator.compute_citation_metrics(generation, retrieval)
                
                # Stage 9: Claim analysis
                logger.info("Analyzing claims")
                faithfulness_report = self.claim_extractor.evaluate_faithfulness(generation, retrieval)
                
                # Build response
                response = QueryResponse(
                    question=question,
                    answer=generation.answer,
                    support_level=generation.support_level.value,
                    confidence=generation.confidence,
                    citations=generation.citations,
                    contradictions=generation.contradictions,
                    retrieval_metadata={
                        **retrieval.method_details,
                        "query_type": query_type.value,
                        "evidence_assessment": evidence_assessment.model_dump(),
                        "citation_metrics": citation_metrics,
                        "faithfulness_report": {
                            "total_claims": faithfulness_report.total_claims,
                            "supported_claims": faithfulness_report.supported_claims,
                            "unsupported_claims": faithfulness_report.unsupported_claims,
                            "claim_level_faithfulness": faithfulness_report.claim_level_faithfulness,
                            "hallucination_rate": faithfulness_report.hallucination_rate,
                        },
                    },
                    evidence_assessment=evidence_assessment,
                    latency={
                        "retrieval_ms": retrieval.retrieval_latency_ms,
                        "generation_ms": generation.generation_latency_ms,
                    },
                    token_usage=generation.token_usage,
                    abstained=generation.abstained,
                )
                
                # Add numerical result if available
                if numerical_result and numerical_result.result is not None:
                    response.retrieval_metadata["numerical_reasoning"] = {
                        "operation": numerical_result.operation.value,
                        "result": numerical_result.result,
                        "unit": numerical_result.unit,
                        "confidence": numerical_result.confidence,
                        "reasoning": numerical_result.reasoning,
                    }
                
                trace.add_event("response_assembly", {
                    "abstained": response.abstained,
                    "support_level": response.support_level,
                })
                
                tracer.end_trace(trace)
                
                logger.info(f"Query processed successfully: {query_id}")
                return response
                
            except Exception as e:
                logger.error(f"Query processing failed: {e}", exc_info=True)
                self.error_count += 1
                raise QueryProcessingError(f"Query processing failed: {e}") from e
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get pipeline health status."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "status": "healthy",
            "uptime_seconds": uptime,
            "query_count": self.query_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.query_count, 1),
            "vector_index_size": self.vector_index.count(),
            "bm25_index_size": self.bm25_index.count(),
            "configuration": config.to_dict(),
        }
    
    def get_diagnostics(self) -> Dict[str, Any]:
        """Get detailed diagnostic information."""
        return {
            "health": self.get_health_status(),
            "components": {
                "parser": "initialized" if self.parser else "not initialized",
                "embedder": "initialized" if self.embedder else "not initialized",
                "vector_index": "initialized" if self.vector_index else "not initialized",
                "bm25_index": "initialized" if self.bm25_index else "not initialized",
                "retriever": "initialized" if self.retriever else "not initialized",
                "generator": "initialized" if self.generator else "not initialized",
            },
            "recent_queries": self.query_count,
            "recent_errors": self.error_count,
        }
    
    def clear_indexes(self) -> None:
        """Clear all indexes (use with caution)."""
        logger.warning("Clearing all indexes")
        self.vector_index.clear()
        # Note: BM25 index would need to be rebuilt
        logger.info("Indexes cleared")


# Global pipeline instance
pipeline = RAGPipeline()


def ingest_document(file_path: str) -> Dict[str, Any]:
    """Convenience function for document ingestion."""
    return pipeline.ingest_document(file_path)


def query(question: str) -> QueryResponse:
    """Convenience function for querying."""
    return pipeline.query(question)


def get_health_status() -> Dict[str, Any]:
    """Get pipeline health status."""
    return pipeline.get_health_status()


def get_diagnostics() -> Dict[str, Any]:
    """Get detailed diagnostics."""
    return pipeline.get_diagnostics()
