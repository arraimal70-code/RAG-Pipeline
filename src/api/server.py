"""
src/api/server.py — FastAPI server for the RAG pipeline.

Endpoints:
- POST /documents — Upload and ingest a document
- GET /documents — List all documents
- DELETE /documents/{id} — Remove a document
- POST /query — Ask a question
- GET /health — Health check
- GET /metrics — System metrics
"""

import logging
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.core.config import config
from src.parsing.pdf_parser import PDFParser
from src.chunking.chunker import get_chunker
from src.embeddings.embedder import get_embedder
from src.indexing.vector_store import VectorIndex
from src.indexing.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.generator import Generator

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Application state
# ──────────────────────────────────────────────
_document_registry: dict[str, dict] = {}  # doc_id → metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize components on startup."""
    logger.info("Starting RAG Pipeline API...")
    config.validate()
    logger.info("API ready.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="RAG Pipeline API",
    description="Research-grade document-grounded question answering",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Request/Response models
# ──────────────────────────────────────────────
class QueryRequest(BaseModel):
    question: str
    top_k: int = Query(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    query_id: str
    question: str
    answer: str
    support_level: str
    confidence: float
    citations: list[dict]
    retrieval_metadata: dict
    latency: dict
    abstained: bool


class DocumentInfo(BaseModel):
    document_id: str
    filename: str
    num_pages: int
    num_chunks: int
    ingested_at: str


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────
@app.post("/documents", response_model=DocumentInfo)
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a PDF document."""
    # Validate
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")

    # Save file
    doc_id = str(uuid.uuid4())
    save_path = config.DOCUMENTS_DIR / f"{doc_id}_{file.filename}"

    content = await file.read()
    if len(content) > config.security.max_file_size_mb * 1024 * 1024:
        raise HTTPException(413, "File too large")

    with open(save_path, "wb") as f:
        f.write(content)

    # Ingest pipeline
    try:
        parser = PDFParser()
        metadata, page_chunks = parser.parse(save_path)

        chunker = get_chunker(config.chunking.strategy)
        chunks = chunker.chunk(page_chunks, config.chunking)

        embedder = get_embedder()
        embeddings = embedder.embed([c.content for c in chunks])

        from src.core.models import EmbeddedChunk
        embedded = [
            EmbeddedChunk(**c.model_dump(), embedding=e)
            for c, e in zip(chunks, embeddings)
        ]

        vector_index = VectorIndex()
        vector_index.add_chunks(embedded)

        # Update BM25
        bm25 = BM25Index()
        bm25.build(chunks)

        # Register
        _document_registry[metadata.document_id] = {
            "filename": metadata.filename,
            "num_pages": metadata.num_pages,
            "num_chunks": len(chunks),
            "ingested_at": metadata.ingested_at,
        }

        return DocumentInfo(
            document_id=metadata.document_id,
            filename=metadata.filename,
            num_pages=metadata.num_pages,
            num_chunks=len(chunks),
            ingested_at=metadata.ingested_at,
        )

    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        save_path.unlink(missing_ok=True)
        raise HTTPException(500, f"Ingestion failed: {str(e)}")


@app.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    """List all ingested documents."""
    return [
        DocumentInfo(document_id=doc_id, **info)
        for doc_id, info in _document_registry.items()
    ]


@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Remove a document and its chunks from all indexes."""
    if document_id not in _document_registry:
        raise HTTPException(404, "Document not found")

    vector_index = VectorIndex()
    vector_index.delete_by_document(document_id)

    del _document_registry[document_id]
    return {"status": "deleted", "document_id": document_id}


@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Ask a question about ingested documents."""
    if not request.question.strip():
        raise HTTPException(400, "Question cannot be empty")

    query_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        retriever = HybridRetriever()
        retrieval = retriever.retrieve(request.question)

        generator = Generator()
        generation = generator.generate(request.question, retrieval)

        total_latency = (time.time() - start_time) * 1000

        return QueryResponse(
            query_id=query_id,
            question=request.question,
            answer=generation.answer,
            support_level=generation.support_level.value,
            confidence=generation.confidence,
            citations=[c.model_dump() for c in generation.citations],
            retrieval_metadata={
                "total_candidates": retrieval.total_candidates,
                "retrieval_latency_ms": retrieval.retrieval_latency_ms,
                "method_details": retrieval.method_details,
            },
            latency={
                "retrieval_ms": retrieval.retrieval_latency_ms,
                "generation_ms": generation.generation_latency_ms,
                "total_ms": total_latency,
            },
            abstained=generation.abstained,
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(500, f"Query failed: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    vector_index = VectorIndex()
    return {
        "status": "healthy",
        "vector_store_count": vector_index.count(),
        "documents_ingested": len(_document_registry),
    }


@app.get("/metrics")
async def metrics():
    """System metrics."""
    vector_index = VectorIndex()
    bm25 = BM25Index()
    return {
        "vector_chunks": vector_index.count(),
        "bm25_chunks": bm25.count(),
        "documents": len(_document_registry),
        "config": {
            "chunking_strategy": config.chunking.strategy,
            "embedding_provider": config.embedding.provider,
            "llm_model": config.generation.model,
            "retrieval_fusion": config.retrieval.fusion_method,
        },
    }
