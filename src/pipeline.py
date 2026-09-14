"""
src/pipeline.py — Complete integrated RAG pipeline.

Integrates all components:
- Document parsing
- Chunking (4 strategies)
- Embedding
- Indexing (vector + BM25)
- Query analysis (adaptive retrieval)
- Hybrid retrieval with RRF
- Reranking
- Evidence sufficiency assessment
- Numerical reasoning
- Temporal reasoning
- LLM generation
- Citation validation
- Claim-level analysis
- Tracing/observability
"""

import logging
import time
from pathlib import Path
from typing import Optional

from src.core.config import config
from src.core.models import (
    TextChunk, EmbeddedChunk, RetrievalOutput,
    GenerationOutput, QueryResponse, SupportLevel,
)
from src.parsing.pdf_parser import PDFParser
from src.chunking.chunker import get_chunker
from src.embeddings.embedder import get_embedder
from src.indexing.vector_store import VectorIndex
from src.indexing.bm25_index import BM25Index
from src.adaptive.query_analyzer import QueryAnalyzer
from src.retrieval.hybrid_retriever import HybridRetriever
from src.reasoning.numerical import NumericalReasoner
from src.reasoning.temporal import TemporalReasoner
from src.evidence.sufficiency import EvidenceSufficiencyChecker
from src.generation.generator import Generator
from src.citations.validator import CitationValidator
from src.claims.extractor import ClaimExtractor
from src.observability.tracing import tracer

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    Complete RAG pipeline with all components integrated.

    Pipeline stages:
    1. Query analysis (classify query type)
    2. Retrieval (hybrid with adaptive weights)
    3. Reranking (cross-encoder)
    4. Evidence sufficiency assessment
    5. Numerical reasoning (if applicable)
    6. Temporal reasoning (if applicable)
    7. LLM generation
    8. Citation validation
    9. Claim-level analysis
    10. Response assembly
    """

    def __init__(self):
        """Initialize all pipeline components."""
        self.parser = PDFParser()
        self.embedder = get_embedder()
        self.vector_index = VectorIndex()
        self.bm25_index = BM25Index()
        self.query_analyzer = QueryAnalyzer()
        self.retriever = HybridRetriever()
        self.numerical_reasoner = NumericalReasoner()
        self.temporal_reasoner = TemporalReasoner()
        self.evidence_checker = EvidenceSufficiencyChecker()
        self.generator = Generator()
        self.citation_validator = CitationValidator()
        self.claim_extractor = ClaimExtractor()

        logger.info("RAG Pipeline initialized with all components")

    def ingest_document(self, file_path: Path) -> dict:
        """
        Ingest a document into the system.

        Steps:
        1. Parse PDF
        2. Chunk text
        3. Generate embeddings
        4. Store in vector index
        5. Build BM25 index

        Returns metadata about ingestion.
        """
        start_time = time.time()

        # Parse
        logger.info(f"Parsing {file_path.name}")
        metadata, page_chunks = self.parser.parse(file_path)

        # Chunk
        logger.info(f"Chunking with strategy: {config.chunking.strategy}")
        chunker = get_chunker(config.chunking.strategy)
        chunks = chunker.chunk(page_chunks, config.chunking)

        # Embed
        logger.info(f"Embedding {len(chunks)} chunks")
        texts = [c.content for c in chunks]
        embeddings = self.embedder.embed(texts)

        # Create embedded chunks
        embedded_chunks = [
            EmbeddedChunk(**c.model_dump(), embedding=e)
            for c, e in zip(chunks, embeddings)
        ]

        # Store
        logger.info("Storing in vector index")
        self.vector_index.add_chunks(embedded_chunks)

        # Build BM25
        logger.info("Building BM25 index")
        self.bm25_index.build(chunks)

        elapsed = (time.time() - start_time) * 1000

        return {
            "document_id": metadata.document_id,
            "filename": metadata.filename,
            "num_pages": metadata.num_pages,
            "num_chunks": len(chunks),
            "ingestion_time_ms": elapsed,
        }

    def query(self, question: str) -> QueryResponse:
        """
        Answer a question using the full pipeline.

        Steps:
        1. Start trace
        2. Analyze query
        3. Retrieve evidence
        4. Apply temporal filtering
        5. Assess evidence sufficiency
        6. Apply numerical reasoning (if needed)
        7. Generate answer
        8. Validate citations
        9. Extract and evaluate claims
        10. Assemble response
        """
        # Start trace
        trace = tracer.start_trace(question)

        try:
            # Stage 1: Query analysis
            stage_start = time.time()
            query_type = self.query_analyzer.classify(question)
            trace.add_event("query_analysis", {
                "query_type": query_type.value,
            }, latency_ms=(time.time() - stage_start) * 1000)

            # Stage 2: Retrieval
            stage_start = time.time()
            retrieval = self.retriever.retrieve(question)
            trace.add_event("retrieval", {
                "num_candidates": retrieval.total_candidates,
                "method_details": retrieval.method_details,
            }, latency_ms=retrieval.retrieval_latency_ms)

            # Stage 3: Temporal filtering
            stage_start = time.time()
            retrieval = self.temporal_reasoner.filter_by_temporal_relevance(
                question, retrieval
            )
            trace.add_event("temporal_filtering", {
                "candidates_after": len(retrieval.candidates),
            }, latency_ms=(time.time() - stage_start) * 1000)

            # Stage 4: Evidence sufficiency
            stage_start = time.time()
            evidence_assessment = self.evidence_checker.assess(question, retrieval)
            trace.add_event("evidence_assessment", {
                "is_sufficient": evidence_assessment.is_sufficient,
                "confidence": evidence_assessment.confidence,
                "recommendation": evidence_assessment.recommendation,
            }, latency_ms=(time.time() - stage_start) * 1000)

            # Check if we should abstain
            if evidence_assessment.recommendation == "abstain":
                response = QueryResponse(
                    question=question,
                    answer="I don't have sufficient evidence to answer this question reliably.",
                    support_level=SupportLevel.INSUFFICIENT_EVIDENCE,
                    confidence=0.0,
                    citations=[],
                    abstained=True,
                    retrieval_metadata=retrieval.method_details,
                    evidence_assessment=evidence_assessment,
                )
                trace.add_event("abstention", {"reason": "insufficient_evidence"})
                tracer.end_trace(trace)
                return response

            # Stage 5: Numerical reasoning (if applicable)
            stage_start = time.time()
            numerical_result = None
            if query_type.value in ["numerical", "calculation", "comparison"]:
                numerical_result = self.numerical_reasoner.reason_about_question(
                    question, [c.chunk for c in retrieval.candidates]
                )
                if numerical_result:
                    trace.add_event("numerical_reasoning", {
                        "operation": numerical_result.operation.value,
                        "result": numerical_result.result,
                        "confidence": numerical_result.confidence,
                    }, latency_ms=(time.time() - stage_start) * 1000)

            # Stage 6: Generation
            stage_start = time.time()
            generation = self.generator.generate(question, retrieval)
            trace.add_event("generation", {
                "support_level": generation.support_level.value,
                "confidence": generation.confidence,
                "num_citations": len(generation.citations),
            }, latency_ms=generation.generation_latency_ms)

            # Stage 7: Citation validation
            stage_start = time.time()
            generation = self.citation_validator.validate_citations(generation, retrieval)
            citation_metrics = self.citation_validator.compute_citation_metrics(generation, retrieval)
            trace.add_event("citation_validation", {
                "validated": citation_metrics["validated_count"],
                "invalid": citation_metrics["invalid_count"],
                "precision": citation_metrics["citation_precision"],
            }, latency_ms=(time.time() - stage_start) * 1000)

            # Stage 8: Claim-level analysis
            stage_start = time.time()
            faithfulness_report = self.claim_extractor.evaluate_faithfulness(generation, retrieval)
            trace.add_event("claim_analysis", {
                "total_claims": faithfulness_report.total_claims,
                "supported": faithfulness_report.supported_claims,
                "unsupported": faithfulness_report.unsupported_claims,
                "faithfulness": faithfulness_report.claim_level_faithfulness,
            }, latency_ms=(time.time() - stage_start) * 1000)

            # Stage 9: Assemble response
            response = QueryResponse(
                question=question,
                answer=generation.answer,
                support_level=generation.support_level,
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
                "support_level": response.support_level.value,
            })

            tracer.end_trace(trace)
            return response

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            trace.add_event("error", {"error": str(e)})
            tracer.end_trace(trace)
            raise

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            "vector_index_size": self.vector_index.count(),
            "bm25_index_size": self.bm25_index.count(),
            "config": {
                "chunking_strategy": config.chunking.strategy,
                "chunk_size": config.chunking.chunk_size,
                "embedding_provider": config.embedding.provider,
                "rerank_enabled": config.retrieval.rerank_enabled,
                "adaptive_enabled": config.retrieval.adaptive_enabled,
            },
        }


# Global pipeline instance
pipeline = RAGPipeline()


def ingest_document(file_path: Path) -> dict:
    """Convenience function for document ingestion."""
    return pipeline.ingest_document(file_path)


def query(question: str) -> QueryResponse:
    """Convenience function for querying."""
    return pipeline.query(question)


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m src.pipeline <command> [args]")
        print("Commands:")
        print("  ingest <pdf_path>  - Ingest a PDF document")
        print("  query <question>   - Ask a question")
        print("  stats              - Show pipeline statistics")
        sys.exit(1)

    command = sys.argv[1]

    if command == "ingest":
        if len(sys.argv) < 3:
            print("Error: Please provide PDF path")
            sys.exit(1)
        pdf_path = Path(sys.argv[2])
        result = ingest_document(pdf_path)
        print(f"Ingested {result['filename']}: {result['num_chunks']} chunks")

    elif command == "query":
        if len(sys.argv) < 3:
            print("Error: Please provide question")
            sys.exit(1)
        question = " ".join(sys.argv[2:])
        response = query(question)
        print(f"\nQuestion: {response.question}")
        print(f"Answer: {response.answer}")
        print(f"Confidence: {response.confidence:.2f}")
        print(f"Support: {response.support_level.value}")
        if response.citations:
            print(f"\nCitations ({len(response.citations)}):")
            for c in response.citations:
                print(f"  - {c.filename} p.{c.page_number + 1}")

    elif command == "stats":
        stats = pipeline.get_stats()
        print(f"Vector index: {stats['vector_index_size']} chunks")
        print(f"BM25 index: {stats['bm25_index_size']} chunks")
        print(f"Config: {stats['config']}")

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
