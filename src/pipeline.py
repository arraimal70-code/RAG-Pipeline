"""
Production-ready RAG Pipeline with comprehensive error handling, monitoring, and validation.
"""

import re
import time
import logging
import json
import uuid
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
from src.adaptive.query_decomposer import QueryDecomposer
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.hyde import HypotheticalDocumentGenerator
from src.reasoning.numerical import NumericalReasoner
from src.reasoning.temporal import TemporalReasoner
from src.evidence.sufficiency import EvidenceSufficiencyChecker
from src.evidence.crag import CorrectiveRAGEngine
from src.generation.generator import Generator
from src.citations.validator import CitationValidator
from src.claims.extractor import ClaimExtractor
from src.cache.semantic_cache import SemanticCache
from src.graph.graph_rag import GraphRAGEngine
from src.agentic.planner import AgenticRAGPlanner, AgenticPlanResult
from src.retrieval.hierarchical import HierarchicalRetriever, HierarchicalChunker
from src.retrieval.mmr import MaximalMarginalRelevanceReranker
from src.retrieval.late_interaction import LateInteractionScorer
from src.retrieval.prf import PseudoRelevanceFeedbackEngine
from src.adaptive.query_rewriter import QueryRewriter
from src.parsing.table_parser import TableParser
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
        
        # Advanced SOTA & GOD-LEVEL components
        self.query_decomposer = QueryDecomposer()
        self.hyde_generator = HypotheticalDocumentGenerator(self.embedder)
        self.crag_engine = CorrectiveRAGEngine()
        self.semantic_cache = SemanticCache(embedder=self.embedder)
        self.graph_engine = GraphRAGEngine()
        self.agentic_planner = AgenticRAGPlanner()
        self.hierarchical_retriever = HierarchicalRetriever()
        self.mmr_reranker = MaximalMarginalRelevanceReranker(embedder=self.embedder)
        self.late_interaction_scorer = LateInteractionScorer()
        self.prf_engine = PseudoRelevanceFeedbackEngine(embedder=self.embedder)
        self.query_rewriter = QueryRewriter()
        self.table_parser = TableParser()
        
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
                
                # Linearize tabular matrices to preserve column-row semantic associations
                for page in page_chunks:
                    if "|" in page.content:
                        page.content = self.table_parser.linearize_document_tables(page.content)

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
                
                # Index into Knowledge Graph
                logger.info("Indexing chunks into Knowledge Graph")
                for c in chunks:
                    self.graph_engine.index_chunk(c)
                
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

    def clear(self) -> None:
        """Clear all indexed documents, vector store, lexical indices, graph, and caches."""
        self.vector_index.clear()
        self.bm25_index.clear()
        self.semantic_cache.clear()
        self.graph_engine.clear()
        self.hierarchical_retriever.clear()
        logger.info("Pipeline indices, graph, and caches cleared.")

    def agentic_query(self, question: str) -> AgenticPlanResult:
        """
        Execute an autonomous multi-step ReAct agent plan with iterative retrieval,
        dynamic drill-down, and cross-document synthesis.
        """
        return self.agentic_planner.execute_plan(question, self)
    
    def query(
        self,
        question: str,
        use_cache: bool = True,
        use_hyde: bool = False,
        use_mmr: bool = False,
        use_graph: bool = True,
        use_maxsim: bool = False,
        use_prf: bool = False,
        use_rewriter: bool = True,
        dialogue_history: Optional[List[str]] = None,
        context_entity: Optional[str] = None,
    ) -> QueryResponse:
        """
        Process a query through the full pipeline with comprehensive validation.
        
        Args:
            question: The question to answer
            use_cache: Whether to check/populate the semantic cache
            use_hyde: Whether to apply Hypothetical Document Embeddings
            use_mmr: Whether to apply Maximal Marginal Relevance diversity reranking
            use_graph: Whether to enrich query response with GraphRAG entity networks
            use_maxsim: Whether to apply ColBERT-style Late-Interaction token MaxSim scoring
            use_prf: Whether to apply Rocchio Pseudo-Relevance Feedback query expansion
            use_rewriter: Whether to normalize coreferences, temporal expressions, and acronyms
            dialogue_history: Optional prior messages for coreference resolution
            context_entity: Optional explicit antecedent entity (e.g. 'Apple')
            
        Returns:
            QueryResponse with answer, citations, and metadata
            
        Raises:
            QueryProcessingError: If query processing fails
        """
        if not question or not isinstance(question, str):
            raise QueryProcessingError("Query cannot be empty or non-string")

        # Stage 0: Conversational coreference resolution and temporal query rewriting
        rewrite_meta = None
        if use_rewriter:
            rw = self.query_rewriter.rewrite(
                question,
                dialogue_history=dialogue_history,
                context_entity=context_entity,
            )
            if rw.is_rewritten:
                logger.info(f"Query rewritten: '{question}' -> '{rw.rewritten_query}'")
                rewrite_meta = {
                    "original_query": rw.original_query,
                    "rewritten_query": rw.rewritten_query,
                    "coreferences": rw.coreferences_resolved,
                    "temporal_anchors": rw.temporal_anchors_applied,
                    "expanded_acronyms": rw.expanded_acronyms,
                }
                question = rw.rewritten_query

        # Fast-path: Semantic Cache check (<5ms)
        if use_cache:
            cached_resp = self.semantic_cache.get(question)
            if cached_resp is not None:
                return cached_resp
            
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
                if use_hyde:
                    hyde_emb = self.hyde_generator.generate_hyde_embedding(question)
                    retrieval = self.retriever.retrieve(question, policy=policy, query_embedding=hyde_emb)
                    retrieval.method_details["hyde"] = {"enabled": True}
                else:
                    retrieval = self.retriever.retrieve(question, policy=policy)

                # Stage 3b: Rocchio Pseudo-Relevance Feedback (PRF) Query Expansion
                if use_prf and retrieval.candidates:
                    logger.info("Applying Rocchio Pseudo-Relevance Feedback (PRF)")
                    prf_res, exp_vec = self.prf_engine.expand_query(question, retrieval.candidates)
                    retrieval.method_details["prf"] = {
                        "expanded_query": prf_res.expanded_query,
                        "expansion_terms": [t[0] for t in prf_res.expansion_terms],
                        "drift_cosine": prf_res.dense_vector_drift,
                        "drift_guarded": prf_res.drift_guarded,
                    }
                    if not prf_res.drift_guarded and prf_res.expanded_query != question:
                        extra_dense = self.vector_index.search(exp_vec, top_k=min(3, policy.dense_top_k))
                        existing_ids = {c.chunk.chunk_id for c in retrieval.candidates}
                        for h in extra_dense:
                            chunk_id = h["chunk_id"] if isinstance(h, dict) else getattr(h, "chunk_id", str(uuid.uuid4()))
                            if chunk_id not in existing_ids:
                                if isinstance(h, dict):
                                    meta = h.get("metadata", {})
                                    chunk = TextChunk(
                                        chunk_id=chunk_id,
                                        document_id=meta.get("document_id", ""),
                                        filename=meta.get("filename", ""),
                                        page_number=meta.get("page_number", 1),
                                        section=meta.get("section", ""),
                                        content=h.get("content", ""),
                                        metadata=meta,
                                    )
                                    score = float(h.get("score", 0.60))
                                else:
                                    chunk = h
                                    score = 0.60
                                retrieval.candidates.append(
                                    RetrievalResult(
                                        chunk=chunk,
                                        score=score,
                                        retrieval_method="dense+prf",
                                        rank=len(retrieval.candidates) + 1,
                                    )
                                )
                                existing_ids.add(chunk_id)
                        retrieval.total_candidates = len(retrieval.candidates)

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

                # Stage 4b: MMR Diversity Reranking
                if use_mmr and len(retrieval.candidates) > 1:
                    logger.info("Applying Maximal Marginal Relevance (MMR) diversity reranking")
                    retrieval.candidates = self.mmr_reranker.rerank(
                        question, retrieval.candidates, top_k=min(5, len(retrieval.candidates))
                    )
                    retrieval.total_candidates = len(retrieval.candidates)
                    retrieval.method_details["mmr"] = {"enabled": True}

                # Stage 4c: ColBERT-style Late-Interaction Token MaxSim Scoring
                if use_maxsim and retrieval.candidates:
                    logger.info("Applying ColBERT-style Late-Interaction MaxSim scoring")
                    retrieval.candidates = self.late_interaction_scorer.rerank(
                        question, retrieval.candidates, top_k=min(5, len(retrieval.candidates))
                    )
                    retrieval.total_candidates = len(retrieval.candidates)
                    retrieval.method_details["late_interaction"] = {"enabled": True}
                
                # Stage 5: Evidence sufficiency assessment
                logger.info("Assessing evidence sufficiency")
                evidence_assessment = self.evidence_checker.assess(question, retrieval)
                trace.add_event("evidence_assessment", {
                    "is_sufficient": evidence_assessment.is_sufficient,
                    "confidence": evidence_assessment.confidence,
                    "recommendation": evidence_assessment.recommendation,
                })

                # CRAG Knowledge Evaluation
                crag_assessment = self.crag_engine.evaluate_retrieval(question, retrieval)
                trace.add_event("crag_evaluation", {
                    "action": crag_assessment.action.value,
                    "confidence_score": crag_assessment.confidence_score,
                    "refined_strips_count": len(crag_assessment.refined_strips),
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
                
                # Stage 10: Self-RAG Reflection Critique
                self_critique = self.crag_engine.self_reflect_critique(
                    question, response.answer, [c.chunk for c in retrieval.candidates]
                )
                response.retrieval_metadata["crag_action"] = crag_assessment.action.value
                response.retrieval_metadata["self_rag_critique"] = {
                    "is_relevant": self_critique.is_relevant,
                    "is_supported": self_critique.is_supported,
                    "utility_score": self_critique.utility_score,
                    "notes": self_critique.critique_notes,
                }

                # Stage 11: GraphRAG Entity & Community Context
                if use_graph:
                    graph_meta = self.graph_engine.global_query(question)
                    response.retrieval_metadata["graph_rag"] = {
                        "seed_entities": graph_meta["seed_entities"],
                        "matched_communities": len(graph_meta["matched_communities"]),
                        "total_graph_nodes": graph_meta["total_graph_nodes"],
                        "total_graph_edges": graph_meta["total_graph_edges"],
                    }

                # Attach query rewrite telemetry if active
                if rewrite_meta:
                    response.retrieval_metadata["query_rewrite"] = rewrite_meta

                # Populate semantic cache if answer is verified and not abstained
                if use_cache and not response.abstained and response.confidence >= 0.5:
                    self.semantic_cache.put(question, response)

                trace.add_event("response_assembly", {
                    "abstained": response.abstained,
                    "support_level": response.support_level,
                    "self_critique": response.retrieval_metadata["self_rag_critique"],
                })
                
                tracer.end_trace(trace)
                
                logger.info(f"Query processed successfully: {query_id}")
                return response
                
            except Exception as e:
                msg = str(e)
                if "sk-" in msg or "key" in msg.lower():
                    msg = re.sub(r'sk-[a-zA-Z0-9_\-]+', '[REDACTED]', msg)
                logger.error(f"Query processing failed: {msg}", exc_info=True)
                self.error_count += 1
                raise QueryProcessingError(f"Query processing failed: {msg}") from e
    
    def linearize_table(self, text: str) -> str:
        """Linearize Markdown and tabular matrices into explicit semantic row-column statements."""
        return self.table_parser.linearize_document_tables(text)

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline operational statistics."""
        return {
            "vector_index_size": self.vector_index.count(),
            "bm25_index_size": self.bm25_index.count(),
            "config": config.to_dict(),
            "query_count": self.query_count,
            "error_count": self.error_count,
        }

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
            "config": config.to_dict(),
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


# Lazy pipeline singleton
_pipeline_instance: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance


class _LazyPipelineProxy:
    def __getattr__(self, name):
        return getattr(get_pipeline(), name)


pipeline = _LazyPipelineProxy()


def ingest_document(file_path: str) -> Dict[str, Any]:
    """Convenience function for document ingestion."""
    return get_pipeline().ingest_document(file_path)


def query(question: str) -> QueryResponse:
    """Convenience function for querying."""
    return get_pipeline().query(question)


def get_health_status() -> Dict[str, Any]:
    """Get pipeline health status."""
    return get_pipeline().get_health_status()


def get_diagnostics() -> Dict[str, Any]:
    """Get detailed diagnostics."""
    return get_pipeline().get_diagnostics()
