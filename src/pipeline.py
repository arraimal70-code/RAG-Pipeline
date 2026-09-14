"""
src/pipeline.py — Main pipeline orchestrator.

Ties together all stages:
1. Parse documents
2. Chunk text
3. Generate embeddings
4. Build indexes (vector + BM25)
5. Answer queries

This is the entry point for both CLI and API usage.
"""

import logging
import sys
import time
from pathlib import Path

from src.core.config import config
from src.parsing.pdf_parser import PDFParser
from src.chunking.chunker import get_chunker
from src.embeddings.embedder import get_embedder
from src.indexing.vector_store import VectorIndex
from src.indexing.bm25_index import BM25Index
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.generator import Generator
from src.core.models import EmbeddedChunk

logging.basicConfig(
    level=getattr(logging, config.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def ingest_documents(documents_dir: Path | None = None) -> None:
    """
    Full ingestion pipeline.

    1. Parse all PDFs in the documents directory
    2. Chunk the text
    3. Generate embeddings
    4. Store in vector index
    5. Build BM25 index
    """
    docs_dir = documents_dir or config.DOCUMENTS_DIR

    if not docs_dir.exists():
        logger.error(f"Documents directory not found: {docs_dir}")
        sys.exit(1)

    pdf_files = list(docs_dir.glob("*.pdf"))
    if not pdf_files:
        logger.error(f"No PDF files found in {docs_dir}")
        sys.exit(1)

    logger.info(f"Found {len(pdf_files)} PDF(s) to ingest")

    parser = PDFParser()
    chunker = get_chunker(config.chunking.strategy)
    embedder = get_embedder()
    vector_index = VectorIndex()

    all_chunks = []

    for pdf_path in pdf_files:
        logger.info(f"Processing: {pdf_path.name}")

        # Parse
        metadata, page_chunks = parser.parse(pdf_path)
        logger.info(f"  Parsed: {metadata.num_pages} pages")

        # Chunk
        chunks = chunker.chunk(page_chunks, config.chunking)
        logger.info(f"  Chunked: {len(chunks)} chunks ({config.chunking.strategy})")

        all_chunks.extend(chunks)

    if not all_chunks:
        logger.warning("No chunks produced. Check your documents and chunking config.")
        return

    # Embed (batched)
    logger.info(f"Embedding {len(all_chunks)} chunks...")
    start = time.time()
    texts = [c.content for c in all_chunks]
    embeddings = embedder.embed(texts)
    elapsed = time.time() - start
    logger.info(f"  Embedded in {elapsed:.1f}s ({len(texts)/elapsed:.0f} chunks/sec)")

    # Store in vector index
    embedded_chunks = [
        EmbeddedChunk(**c.model_dump(), embedding=e)
        for c, e in zip(all_chunks, embeddings)
    ]
    vector_index.add_chunks(embedded_chunks)

    # Build BM25 index
    bm25 = BM25Index()
    bm25.build(all_chunks)

    logger.info(
        f"✅ Ingestion complete: {len(all_chunks)} chunks indexed "
        f"(vector: {vector_index.count()}, bm25: {bm25.count()})"
    )


def query(question: str) -> dict:
    """
    Answer a single question.

    Returns structured response with answer, citations, and metadata.
    """
    retriever = HybridRetriever()
    generator = Generator()

    # Retrieve
    retrieval = retriever.retrieve(question)

    # Generate
    generation = generator.generate(question, retrieval)

    return {
        "answer": generation.answer,
        "support_level": generation.support_level.value,
        "confidence": generation.confidence,
        "citations": [
            {
                "filename": c.filename,
                "page": c.page_number + 1,
                "section": c.section,
                "evidence": c.relevant_text[:200],
            }
            for c in generation.citations
        ],
        "abstained": generation.abstained,
        "latency": {
            "retrieval_ms": retrieval.retrieval_latency_ms,
            "generation_ms": generation.generation_latency_ms,
        },
    }


def interactive_loop() -> None:
    """Interactive CLI query loop."""
    print("=" * 60)
    print("  RAG Pipeline — Interactive Query")
    print("=" * 60)
    print()

    vector_index = VectorIndex()
    count = vector_index.count()
    if count == 0:
        print("⚠️  No documents indexed. Run: python -m src.pipeline ingest")
        return

    print(f"📚 {count} chunks indexed. Ask a question:")
    print("   Type 'quit' to exit.\n")

    while True:
        try:
            question = input("❓ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question or question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        result = query(question)

        print()
        if result["abstained"]:
            print(f"⚠️  {result['answer']}")
        else:
            print(f"💬 {result['answer']}")

        print(f"\n📊 Confidence: {result['confidence']:.0%} | "
              f"Support: {result['support_level']}")

        if result["citations"]:
            print("\n📎 Sources:")
            for c in result["citations"]:
                page_info = f"p.{c['page']}" if c['page'] else ""
                section_info = f" [{c['section']}]" if c.get('section') else ""
                print(f"  • {c['filename']} {page_info}{section_info}")

        print(f"\n⏱️  Retrieval: {result['latency']['retrieval_ms']:.0f}ms | "
              f"Generation: {result['latency']['generation_ms']:.0f}ms")
        print("─" * 60)
        print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ingest":
        ingest_documents()
    else:
        interactive_loop()
