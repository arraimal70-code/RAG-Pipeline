"""
Production-ready API server with comprehensive monitoring and security.
"""

import logging
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.pipeline import pipeline, QueryProcessingError, DocumentIngestionError
from src.core.models import QueryResponse
from src.security.enhanced_security import (
    get_document_validator,
    get_query_validator,
    get_rate_limiter,
    get_security_audit_logger,
)
from src.monitoring.metrics import get_metrics_collector, get_health_checker, QueryMetrics
from src.core.config import config

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    user_id: Optional[str] = "anonymous"


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    num_pages: int
    num_chunks: int
    status: str


class HealthResponse(BaseModel):
    status: str
    uptime_seconds: float
    query_count: int
    error_count: int
    error_rate: float
    vector_index_size: int
    bm25_index_size: int


class DiagnosticsResponse(BaseModel):
    health: dict
    components: dict
    recent_queries: int
    recent_errors: int


# ──────────────────────────────────────────────
# Dependency injection
# ──────────────────────────────────────────────
async def get_user_id(request: Request) -> str:
    """Extract user ID from request."""
    # In production, would extract from JWT token or session
    return request.headers.get("X-User-ID", "anonymous")


async def check_rate_limit(user_id: str = Depends(get_user_id)):
    """Check rate limit for user."""
    rate_limiter = get_rate_limiter()
    is_allowed, metadata = rate_limiter.check_rate_limit(user_id)
    
    if not is_allowed:
        audit_logger = get_security_audit_logger()
        audit_logger.log_rate_limit_exceeded(
            user_id=user_id,
            limit=metadata["limit"],
            retry_after=metadata["retry_after_seconds"],
        )
        
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "retry_after_seconds": metadata["retry_after_seconds"],
            },
            headers={
                "Retry-After": str(int(metadata["retry_after_seconds"])),
            },
        )
    
    return user_id


# ──────────────────────────────────────────────
# Application lifecycle
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    logger.info("Starting RAG Pipeline API...")
    
    # Validate configuration
    try:
        config.validate()
        logger.info("Configuration validated successfully")
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise
    
    logger.info("API ready")
    yield
    logger.info("Shutting down API")


# ──────────────────────────────────────────────
# FastAPI application
# ──────────────────────────────────────────────
app = FastAPI(
    title="RAG Pipeline API",
    description="Research-grade document-grounded question answering",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Exception handlers
# ──────────────────────────────────────────────
@app.exception_handler(QueryProcessingError)
async def query_processing_error_handler(request: Request, exc: QueryProcessingError):
    """Handle query processing errors."""
    logger.error(f"Query processing error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Query processing failed", "detail": str(exc)},
    )


@app.exception_handler(DocumentIngestionError)
async def document_ingestion_error_handler(request: Request, exc: DocumentIngestionError):
    """Handle document ingestion errors."""
    logger.error(f"Document ingestion error: {exc}")
    return JSONResponse(
        status_code=400,
        content={"error": "Document ingestion failed", "detail": str(exc)},
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@app.post("/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    user_id: str = Depends(check_rate_limit),
):
    """
    Process a query and return an answer with citations.
    
    - Validates query for security
    - Checks rate limits
    - Processes query through full pipeline
    - Records metrics
    """
    start_time = time.perf_counter()
    
    # Validate query
    query_validator = get_query_validator()
    is_safe, reason = query_validator.validate(request.question)
    
    if not is_safe:
        audit_logger = get_security_audit_logger()
        patterns = query_validator.detect_injection_attempts(request.question)
        audit_logger.log_injection_attempt(
            user_id=user_id,
            query=request.question,
            patterns_detected=patterns,
        )
        
        # Sanitize query
        request.question = query_validator.sanitize(request.question)
        logger.warning(f"Query sanitized for user {user_id}: {reason}")
    
    try:
        # Process query
        response = pipeline.query(request.question)
        
        # Record metrics
        latency_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector = get_metrics_collector()
        
        query_metrics = QueryMetrics(
            query_id=f"query_{int(time.time())}",
            timestamp=response.retrieval_metadata.get("timestamp", ""),
            query_text=request.question,
            query_type=response.retrieval_metadata.get("query_type", "unknown"),
            latency_ms=latency_ms,
            retrieval_latency_ms=response.latency.get("retrieval_ms", 0.0),
            generation_latency_ms=response.latency.get("generation_ms", 0.0),
            num_candidates=response.retrieval_metadata.get("num_candidates", 0),
            num_citations=len(response.citations),
            confidence=response.confidence,
            support_level=response.support_level,
            abstained=response.abstained,
            token_usage=response.token_usage,
        )
        
        metrics_collector.record_query(query_metrics)
        
        return response
        
    except Exception as e:
        logger.error(f"Query failed: {e}", exc_info=True)
        raise QueryProcessingError(str(e))


@app.post("/documents", response_model=DocumentInfo)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(check_rate_limit),
):
    """
    Upload and ingest a document.
    
    - Validates document for security
    - Checks file size and type
    - Ingests document into indexes
    """
    # Save file temporarily
    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_path = temp_dir / f"{user_id}_{file.filename}"
    
    try:
        # Save file
        content = await file.read()
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Validate document
        doc_validator = get_document_validator()
        is_valid, reason = doc_validator.validate(temp_path)
        
        if not is_valid:
            audit_logger = get_security_audit_logger()
            audit_logger.log_document_validation_failure(
                user_id=user_id,
                file_path=str(temp_path),
                reason=reason,
            )
            raise HTTPException(status_code=400, detail=f"Document validation failed: {reason}")
        
        # Ingest document
        result = pipeline.ingest_document(str(temp_path))
        
        return DocumentInfo(
            document_id=result["document_id"],
            filename=result["filename"],
            num_pages=result["num_pages"],
            num_chunks=result["num_chunks"],
            status=result["status"],
        )
        
    except Exception as e:
        logger.error(f"Document upload failed: {e}", exc_info=True)
        raise DocumentIngestionError(str(e))
    
    finally:
        # Clean up temporary file
        if temp_path.exists():
            temp_path.unlink()


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns system health status and basic metrics.
    """
    health = pipeline.get_health_status()
    
    return HealthResponse(
        status=health["status"],
        uptime_seconds=health["uptime_seconds"],
        query_count=health["query_count"],
        error_count=health["error_count"],
        error_rate=health["error_rate"],
        vector_index_size=health["vector_index_size"],
        bm25_index_size=health["bm25_index_size"],
    )


@app.get("/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics():
    """
    Detailed diagnostics endpoint.
    
    Returns comprehensive system diagnostics.
    """
    diag = pipeline.get_diagnostics()
    
    return DiagnosticsResponse(
        health=diag["health"],
        components=diag["components"],
        recent_queries=diag["recent_queries"],
        recent_errors=diag["recent_errors"],
    )


@app.get("/metrics")
async def metrics():
    """
    Metrics endpoint.
    
    Returns comprehensive system metrics.
    """
    metrics_collector = get_metrics_collector()
    return metrics_collector.get_summary()


@app.get("/metrics/queries")
async def query_metrics(limit: int = 100):
    """
    Query metrics endpoint.
    
    Returns recent query metrics.
    """
    metrics_collector = get_metrics_collector()
    return metrics_collector.get_query_metrics(limit=limit)


@app.get("/metrics/health")
async def metrics_health():
    """
    Health check metrics.
    
    Returns detailed health check results.
    """
    health_checker = get_health_checker(pipeline)
    return health_checker.check_all()


@app.post("/cache/clear")
async def clear_cache():
    """
    Clear all caches.
    
    Use with caution - will impact performance until caches are rebuilt.
    """
    from src.cache.cache import cleanup_all_caches
    
    result = cleanup_all_caches()
    logger.info(f"Caches cleared: {result}")
    
    return {
        "status": "success",
        "cleared": result,
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RAG Pipeline API",
        "version": "2.0.0",
        "description": "Research-grade document-grounded question answering",
        "endpoints": {
            "/query": "POST - Process a query",
            "/documents": "POST - Upload a document",
            "/health": "GET - Health check",
            "/diagnostics": "GET - Detailed diagnostics",
            "/metrics": "GET - System metrics",
            "/metrics/queries": "GET - Query metrics",
            "/metrics/health": "GET - Health check metrics",
            "/cache/clear": "POST - Clear caches",
        },
    }


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
