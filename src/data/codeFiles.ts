export interface CodeFile {
  name: string;
  language: string;
  description: string;
  code: string;
}

export const codeFiles: CodeFile[] = [
  {
    name: "config.py",
    language: "python",
    description: "All configurable constants in one place — change these to tune your pipeline.",
    code: `"""
config.py — Central configuration for the RAG pipeline.

All tunable parameters live here so you never have to hunt through
multiple files to change chunk size, model names, or paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # loads .env file for API keys

# ──────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DOCUMENTS_DIR = BASE_DIR / "documents"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"

# ──────────────────────────────────────────────
# Chunking
# ──────────────────────────────────────────────
# Why ~800 tokens?  Research shows LLMs attend best to context
# windows of 500–1000 tokens.  Larger chunks = more context but
# noisier retrieval; smaller = precise but may split ideas mid-sentence.
CHUNK_SIZE = 800       # tokens per chunk
CHUNK_OVERLAP = 150    # overlap preserves context at boundaries

# ──────────────────────────────────────────────
# Embedding model
# ──────────────────────────────────────────────
# Default: free, local, fast.  Swap to OpenAI by changing this one string.
# "openai"  → uses text-embedding-3-small via API (costs ~$0.02/1M tokens)
# "local"   → uses sentence-transformers all-MiniLM-L6-v2 (free, offline)
EMBEDDING_PROVIDER = "local"

# ──────────────────────────────────────────────
# LLM for answer generation
# ──────────────────────────────────────────────
LLM_MODEL = "gpt-4o-mini"   # fast + cheap; swap to "gpt-4o" for quality
LLM_TEMPERATURE = 0.0       # 0 = deterministic, best for factual Q&A

# ──────────────────────────────────────────────
# Retrieval
# ──────────────────────────────────────────────
TOP_K = 4  # number of chunks retrieved per query

# ──────────────────────────────────────────────
# API Keys (loaded from .env)
# ──────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
`
  },
  {
    name: "ingest.py",
    language: "python",
    description: "Stage 1: Load PDFs → chunk → embed → store in Chroma.",
    code: `"""
ingest.py — Stage 1 of the RAG pipeline.

Walks the /documents folder, loads every PDF, splits into overlapping
chunks, embeds them, and persists the vectors in Chroma.

Run:  python ingest.py

The vector store is persistent — re-running only processes NEW files
that aren't already in the database.
"""

import sys
from pathlib import Path

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

from config import (
    DOCUMENTS_DIR,
    CHROMA_PERSIST_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    EMBEDDING_PROVIDER,
)


# ──────────────────────────────────────────────
# 1. Choose the embedding function
# ──────────────────────────────────────────────
def get_embeddings():
    """
    Returns an embedding model based on config.

    DECISION: We default to a local sentence-transformers model so the
    entire pipeline runs at $0 cost during development.  Switching to
    OpenAI embeddings is a one-line config change.
    """
    if EMBEDDING_PROVIDER == "openai":
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small")
    else:
        # Local, free, 384-dim embeddings — good quality for the size
        from langchain_community.embeddings import HuggingFaceEmbeddings
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # cosine similarity
        )


# ──────────────────────────────────────────────
# 2. Load PDFs
# ──────────────────────────────────────────────
def load_documents():
    """
    Loads all PDFs from the documents/ directory.

    PyPDFDirectoryLoader recursively finds every .pdf and extracts text.
    Each page becomes a separate Document with metadata including:
      - source: file path
      - page: page number (0-indexed)
    This metadata is preserved through chunking and stored in Chroma,
    so we can cite exact sources later.
    """
    if not DOCUMENTS_DIR.exists():
        print(f"❌ Documents directory not found: {DOCUMENTS_DIR}")
        print(f"   Create it and add some PDFs:  mkdir -p {DOCUMENTS_DIR}")
        sys.exit(1)

    pdf_files = list(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"❌ No PDF files found in {DOCUMENTS_DIR}")
        sys.exit(1)

    print(f"📄 Found {len(pdf_files)} PDF(s) in {DOCUMENTS_DIR}")

    loader = PyPDFDirectoryLoader(str(DOCUMENTS_DIR))
    documents = loader.load()
    print(f"   Loaded {len(documents)} pages total")
    return documents


# ──────────────────────────────────────────────
# 3. Chunk the documents
# ──────────────────────────────────────────────
def split_documents(documents):
    """
    Splits documents into overlapping chunks.

    DECISION: RecursiveCharacterTextSplitter tries to split on natural
    boundaries (paragraphs → sentences → words) so we rarely cut mid-word.

    Why overlap?  If a key sentence spans a chunk boundary, the overlap
    ensures it appears in BOTH chunks, so retrieval can still find it.

    Chunk size ~800 tokens balances:
      - Enough context for the LLM to understand the passage
      - Small enough that retrieval is precise (not too much noise)
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,  # character-based (approximate for token count)
        separators=["\\n\\n", "\\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"   Split into {len(chunks)} chunks (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})")
    return chunks


# ──────────────────────────────────────────────
# 4. Embed + store in Chroma
# ──────────────────────────────────────────────
def store_in_chroma(chunks):
    """
    Embeds all chunks and stores them in a persistent Chroma database.

    DECISION: Chroma over FAISS because:
      - Persistent storage (survives restarts) — no re-embedding needed
      - Built-in metadata filtering
      - Simple API, no separate server required
      - Free and runs locally

    from_documents() handles both embedding AND storing in one call.
    The persist_directory makes it survive between runs.
    """
    embeddings = get_embeddings()

    print(f"🔧 Embedding {len(chunks)} chunks with '{EMBEDDING_PROVIDER}' model...")
    print(f"   (First run downloads the model; subsequent runs are instant)")

    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_PERSIST_DIR),
    )
    db.persist()  # write to disk

    print(f"✅ Stored in {CHROMA_PERSIST_DIR}")
    print(f"   Database contains {db._collection.count()} vectors")
    return db


# ──────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  RAG Pipeline — Ingestion")
    print("=" * 50)
    print()

    # Step 1: Load
    documents = load_documents()

    # Step 2: Chunk
    chunks = split_documents(documents)

    # Step 3: Embed + Store
    store_in_chroma(chunks)

    print()
    print("🎉 Ingestion complete! You can now run: python query.py")


if __name__ == "__main__":
    main()
`
  },
  {
    name: "query.py",
    language: "python",
    description: "Stage 2: Retrieve relevant chunks → generate answer with citations.",
    code: `"""
query.py — Stage 2 of the RAG pipeline.

Takes a natural-language question, retrieves the most relevant document
chunks from Chroma, sends them to an LLM with a carefully crafted prompt,
and returns the answer with source citations.

Run:  python query.py
Then type your question at the prompt.  Type 'quit' to exit.
"""

import sys

from langchain_community.vectorstores import Chroma
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

from config import (
    CHROMA_PERSIST_DIR,
    EMBEDDING_PROVIDER,
    LLM_MODEL,
    LLM_TEMPERATURE,
    TOP_K,
    OPENAI_API_KEY,
)
from ingest import get_embeddings


# ──────────────────────────────────────────────
# 1. Load the existing vector store
# ──────────────────────────────────────────────
def load_vector_store():
    """
    Loads the Chroma database that was created by ingest.py.

    We use the SAME embedding model that was used during ingestion.
    This is critical — query embeddings must live in the same vector
    space as the stored document embeddings.
    """
    if not CHROMA_PERSIST_DIR.exists():
        print("❌ No vector store found. Run 'python ingest.py' first!")
        sys.exit(1)

    embeddings = get_embeddings()
    db = Chroma(
        persist_directory=str(CHROMA_PERSIST_DIR),
        embedding_function=embeddings,
    )
    count = db._collection.count()
    print(f"📚 Loaded vector store with {count} chunks")
    return db


# ──────────────────────────────────────────────
# 2. Build the retriever
# ──────────────────────────────────────────────
def get_retriever(db):
    """
    Creates a retriever from the vector store.

    DECISION: We use MMR (Maximal Marginal Relevance) instead of plain
    similarity search.  MMR balances:
      - Relevance: how similar the chunk is to the query
      - Diversity: how different the chunks are from each other

    This prevents retrieving 4 nearly-identical chunks and instead
    gives the LLM a broader view of the relevant content.

    search_kwargs:
      - k=TOP_K: number of results to return
      - fetch_k=20: candidates to consider before filtering
    """
    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": TOP_K,
            "fetch_k": 20,  # consider more candidates for diversity
        },
    )
    return retriever


# ──────────────────────────────────────────────
# 3. Define the prompt template
# ──────────────────────────────────────────────
PROMPT_TEMPLATE = """You are a helpful assistant that answers questions based ONLY on the provided context.

Context (retrieved document chunks):
{context}

---

Question: {question}

---

Instructions:
- Answer the question using only the information in the context above.
- If the context doesn't contain enough information to answer, say:
  "I don't have enough information in the provided documents to answer this."
- Be concise but complete.
- Do not make up information or use outside knowledge.
"""


def build_chain(retriever):
    """
    Builds the LangChain retrieval-augmented generation chain.

    The chain has three stages:
    1. Retrieve: get relevant chunks from the vector store
    2. Format: stitch them into the prompt template
    3. Generate: send to the LLM and parse the response

    DECISION: We use LCEL (LangChain Expression Language) with the pipe
    syntax because it's:
      - Readable: you can trace the data flow left-to-right
      - Composable: each step is independently testable
      - Streamable: supports streaming output (future enhancement)
    """
    llm = ChatOpenAI(
        model=LLM_MODEL,
        temperature=LLM_TEMPERATURE,
        api_key=OPENAI_API_KEY,
    )

    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)

    def format_docs(docs):
        """
        Formats retrieved documents into a single context string.
        Each chunk is labeled with its source for the LLM's reference.
        """
        formatted = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            page = doc.metadata.get("page", "?")
            formatted.append(
                f"[Chunk {i}] Source: {source}, Page: {page}\\n{doc.page_content}"
            )
        return "\\n\\n---\\n\\n".join(formatted)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain


# ──────────────────────────────────────────────
# 4. Format sources for display
# ──────────────────────────────────────────────
def format_sources(docs):
    """
    Extracts unique sources from retrieved documents for citation display.
    Shows filename + page number for each relevant chunk.
    """
    sources = []
    seen = set()
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        # Extract just the filename from the full path
        filename = source.split("/")[-1] if "/" in source else source
        key = f"{filename}:p{page}"
        if key not in seen:
            seen.add(key)
            sources.append(f"  • {filename} (page {int(page) + 1})")
    return "\\n".join(sources) if sources else "  • No sources available"


# ──────────────────────────────────────────────
# 5. Interactive query loop
# ──────────────────────────────────────────────
def main():
    print("=" * 50)
    print("  RAG Pipeline — Query Interface")
    print("=" * 50)
    print()

    # Load components
    db = load_vector_store()
    retriever = get_retriever(db)
    chain = build_chain(retriever)

    print()
    print("🤖 Ready! Ask a question about your documents.")
    print("   Type 'quit' or 'exit' to stop.\\n")

    while True:
        try:
            question = input("❓ Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\\n\\nGoodbye! 👋")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye! 👋")
            break

        print()

        # Retrieve documents (for source display)
        docs = retriever.invoke(question)

        # Generate answer
        print("🧠 Thinking...\\n")
        answer = chain.invoke(question)

        # Display results
        print("─" * 50)
        print(f"💬 Answer:\\n")
        print(answer)
        print()
        print(f"📎 Sources:")
        print(format_sources(docs))
        print("─" * 50)
        print()


if __name__ == "__main__":
    main()
`
  },
  {
    name: "requirements.txt",
    language: "text",
    description: "Python dependencies — pip install -r requirements.txt",
    code: `# RAG Pipeline Dependencies
# Install: pip install -r requirements.txt

# Core framework
langchain>=0.3.0
langchain-community>=0.3.0
langchain-openai>=0.2.0

# PDF loading
pypdf>=4.0.0

# Vector store
chromadb>=0.5.0

# Local embeddings (free, no API key needed)
sentence-transformers>=3.0.0

# Environment variables
python-dotenv>=1.0.0
`
  },
  {
    name: ".env.example",
    language: "bash",
    description: "Copy to .env and fill in your API key.",
    code: `# Copy this file to .env and fill in your values:
#   cp .env.example .env

# OpenAI API key (required for LLM generation)
# Get yours at: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-key-here

# Note: If you set EMBEDDING_PROVIDER="local" in config.py,
# you only need the API key for the LLM (answer generation).
# The embedding step runs locally for free.
`
  },
  {
    name: "README.md",
    language: "markdown",
    description: "Project documentation — setup, usage, and architecture.",
    code: `# RAG Pipeline — PDF Question & Answering

A local, educational RAG (Retrieval-Augmented Generation) system that lets
you drop PDF documents into a folder and ask natural-language questions
about their contents. Answers include source citations.

## How It Works

\`\`\`
┌──────────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│  PDF Files   │────▶│  Chunk   │────▶│   Embed    │────▶│  Chroma  │
│  (ingest)    │     │ (split)  │     │(vectors)   │     │  (store) │
└──────────────┘     └──────────┘     └────────────┘     └──────────┘
                                                                  │
                                                                  ▼
┌──────────────┐     ┌──────────┐     ┌────────────┐     ┌──────────┐
│   Answer +   │◀────│   LLM    │◀────│   Build    │◀────│ Retrieve │
│   Sources    │     │(generate)│     │   Prompt   │     │ top-k    │
└──────────────┘     └──────────┘     └────────────┘     └──────────┘
\`\`\`

**Stage 1 (ingest.py):** Load → Chunk → Embed → Store
**Stage 2 (query.py):**  Question → Retrieve → Prompt → Generate → Cite

## Quick Start

### 1. Install dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

### 2. Set up your API key

\`\`\`bash
cp .env.example .env
# Edit .env and add your OpenAI API key
\`\`\`

### 3. Add PDFs

Place your PDF files in the \`documents/\` folder:

\`\`\`bash
mkdir -p documents
cp ~/my-papers/*.pdf documents/
\`\`\`

### 4. Run ingestion

\`\`\`bash
python ingest.py
\`\`\`

This loads all PDFs, splits them into chunks, embeds them, and stores
the vectors in \`chroma_db/\`. Re-running is safe — it rebuilds the store.

### 5. Ask questions

\`\`\`bash
python query.py
\`\`\`

Type your question and get an answer with source citations!

## Configuration

All settings are in \`config.py\`:

| Setting | Default | Description |
|---------|---------|-------------|
| \`CHUNK_SIZE\` | 800 | Characters per chunk |
| \`CHUNK_OVERLAP\` | 150 | Overlap between chunks |
| \`EMBEDDING_PROVIDER\` | "local" | "local" (free) or "openai" |
| \`LLM_MODEL\` | "gpt-4o-mini" | LLM for generation |
| \`TOP_K\` | 4 | Chunks retrieved per query |

## Switching to OpenAI Embeddings

In \`config.py\`, change:
\`\`\`python
EMBEDDING_PROVIDER = "openai"
\`\`\`
Then re-run \`python ingest.py\`. That's it.

## Project Structure

\`\`\`
rag-pipeline/
├── documents/          # Your PDF files go here
├── chroma_db/          # Persisted vector store (auto-created)
├── ingest.py           # Stage 1: load, chunk, embed, store
├── query.py            # Stage 2: retrieve, generate, cite
├── config.py           # All configurable constants
├── requirements.txt    # Python dependencies
├── .env.example        # Template for API keys
├── .env                # Your actual keys (gitignored!)
├── DECISIONS.md        # Architectural decisions explained
└── README.md           # This file
\`\`\`

## Cost Estimate

With default settings (local embeddings + gpt-4o-mini):
- **Embedding:** $0 (local model)
- **Generation:** ~$0.001 per query (gpt-4o-mini is very cheap)
- **Total for 100 queries:** ~$0.10

## Troubleshooting

- **"No PDF files found"** → Make sure PDFs are in \`documents/\` (not a subfolder)
- **"No vector store found"** → Run \`python ingest.py\` first
- **Slow first run** → Normal! Downloading the embedding model takes ~30s
- **Bad answers** → Try increasing \`TOP_K\` or adjusting \`CHUNK_SIZE\`
`
  },
  {
    name: "DECISIONS.md",
    language: "markdown",
    description: "Why we made each architectural choice — the learning companion.",
    code: `# Architectural Decisions

This document explains the reasoning behind key choices in the RAG pipeline.
Read this to understand *why*, not just *what*.

---

## 1. Why RecursiveCharacterTextSplitter?

**Alternatives considered:**
- \`CharacterTextSplitter\` — too simple, splits only on one separator
- \`TokenTextSplitter\` — requires tiktoken, slower, and LLMs don't
  actually need exact token counts for chunking

**Why RecursiveCharacterTextSplitter:**
It tries multiple separators in order: \`["\\n\\n", "\\n", ". ", " ", ""]\`.
This means it prefers splitting at paragraph breaks, then line breaks,
then sentence boundaries — keeping semantic units intact as much as possible.

---

## 2. Why chunk_size=800, overlap=150?

**Chunk size:**
- Too small (<300): Chunks lack context; the LLM can't understand them
- Too large (>1500): Chunks contain too much noise; retrieval precision drops
- 800 is the sweet spot: ~2-3 paragraphs, enough for self-contained meaning

**Overlap:**
- Without overlap: A key fact at a chunk boundary might be split across
  two chunks, and NEITHER chunk has the complete fact
- 150 chars (~2 sentences) of overlap ensures boundary facts survive
- Cost: ~20% more chunks to embed, but much better retrieval quality

---

## 3. Why Chroma over FAISS?

| Feature | Chroma | FAISS |
|---------|--------|-------|
| Persistence | ✅ Built-in | ❌ Manual save/load |
| Metadata filtering | ✅ Native | ❌ Not supported |
| Setup complexity | Low | Medium |
| Server required | No | No |
| Cost | Free | Free |

**Decision:** Chroma wins for a local/educational project because:
- Persistent storage means re-running the app doesn't re-embed everything
- Metadata filtering lets us add features later (e.g., "only search PDF X")
- Simpler API = less code to understand

---

## 4. Why local embeddings by default?

**Trade-offs:**

| | Local (MiniLM) | OpenAI (text-embedding-3-small) |
|---|---|---|
| Cost | $0 | ~$0.02/1M tokens |
| Speed | ~50 chunks/sec | ~1000 chunks/sec |
| Quality | Good (MTEB avg: 56) | Better (MTEB avg: 62) |
| Offline | ✅ Yes | ❌ No |
| Setup | pip install | API key needed |

**Decision:** Local first because:
- Zero cost during development and experimentation
- No API key needed to get started
- Quality is "good enough" for most use cases
- Easy to swap later (one config line)

---

## 5. Why MMR retrieval instead of plain similarity?

**Plain similarity search** returns the top-k most similar chunks.
Problem: If 3 of your top-4 results are from the same paragraph,
you've wasted 3 slots on near-duplicate information.

**MMR (Maximal Marginal Relevance)** balances:
- **Relevance:** How similar is this chunk to the query?
- **Diversity:** How different is this chunk from already-selected ones?

Result: More varied context → better LLM answers.

---

## 6. Why temperature=0.0?

For factual Q&A, we want deterministic, consistent answers.
- temperature=0.0: Most deterministic, picks the most likely token
- temperature=0.7: Creative, varied (good for brainstorming)
- temperature=1.0: Maximum randomness

Since we're asking "what does the document say?", we want the model
to be as faithful to the source as possible. No creative interpretation.

---

## 7. Why gpt-4o-mini instead of gpt-4o?

| Model | Cost/1M tokens | Speed | Quality |
|-------|---------------|-------|---------|
| gpt-4o-mini | $0.15 in / $0.60 out | Fast | Good |
| gpt-4o | $2.50 in / $10.00 out | Slower | Excellent |

For a RAG system where the context is already curated by retrieval,
gpt-4o-mini handles the task well at 1/16th the cost. Upgrade to gpt-4o
if you need nuanced reasoning or very long outputs.

---

## 8. Why separate ingest.py and query.py?

**Separation of concerns:**
- Ingestion is expensive (embedding) and done once
- Querying is cheap and done many times
- Separating them means you can re-query without re-embedding
- Each file has a single responsibility (easier to understand and debug)

**Future extension:** You could add a web server that only imports
the query logic, or a cron job that re-ingests on a schedule.
`
  }
];
