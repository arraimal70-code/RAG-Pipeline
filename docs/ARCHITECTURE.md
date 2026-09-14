# System Architecture

## Overview

The RAG Pipeline follows an adaptive, evidence-aware architecture. Unlike basic RAG systems that use a fixed retrieve-then-generate pipeline, this system dynamically adjusts its retrieval strategy based on query characteristics and assesses evidence sufficiency before generating answers.

## Central Research Question

> How can a RAG system dynamically balance retrieval quality, factual reliability, latency, and computational cost while recognizing when available evidence is insufficient to answer a question?

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         INGESTION PIPELINE                            │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  PDF Files → Parser → Structure Detector → Chunker (4 strategies)    │
│                  ↓                          ↓                         │
│            Metadata                   TextChunks                      │
│            Extraction                      ↓                          │
│                  ↓               ┌────────┼────────┐                 │
│           DocumentMeta          ↓        ↓        ↓                  │
│                              Embedder  BM25    Store                 │
│                                ↓        ↓        ↓                  │
│                           VectorIndex  BM25Idx  ChromaDB             │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                    ADAPTIVE QUERY PIPELINE                             │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Question                                                             │
│     │                                                                 │
│     ├──→ Query Analyzer (classify type)                               │
│     │        │                                                        │
│     │        ├── EXACT → lexical-heavy weights                        │
│     │        ├── CONCEPTUAL → semantic-heavy weights                  │
│     │        ├── MULTI_HOP → broader retrieval                        │
│     │        └── UNKNOWN → balanced hybrid                            │
│     │                                                                 │
│     ├──→ Dense Retrieval (adjusted top-K) ──┐                        │
│     │                                        │                        │
│     └──→ BM25 Retrieval (adjusted top-K) ───┤                        │
│                                              │                        │
│                                              ↓                        │
│                              Adaptive Weighted Fusion                 │
│                                              │                        │
│                                              ↓                        │
│                              Cross-Encoder Reranking                  │
│                                              │                        │
│                                              ↓                        │
│                          Evidence Sufficiency Assessment              │
│                                     │                                 │
│                    ┌────────────────┼────────────────┐               │
│                    ↓                ↓                ↓               │
│              Sufficient      Retrieve More       Abstain             │
│                    │                                               │
│                    ↓                                               │
│              LLM Generation                                        │
│              (with grounding)                                      │
│                    │                                               │
│                    ↓                                               │
│              Citation Validation                                   │
│                    │                                               │
│                    ↓                                               │
│              Contradiction Check                                   │
│                    │                                               │
│                    ↓                                               │
│         ┌──────────┴──────────┐                                   │
│         ↓                     ↓                                    │
│    Answer + Citations    Evaluation + Logging                      │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. Query Analyzer (src/adaptive/)
- Classifies queries into types (EXACT, CONCEPTUAL, MULTI_HOP, etc.)
- Maps query types to optimal retrieval weights
- Adjusts candidate count based on query complexity
- Rule-based (fast, deterministic, debuggable)

### 2. Adaptive Retriever (src/adaptive/)
- Uses query analysis to adjust dense/BM25 weights
- Adjusts candidate counts per query type
- Records all adaptive decisions for experimental analysis
- Falls back to fixed weights when adaptive is disabled

### 3. Evidence Sufficiency (src/evidence/)
- Assesses retrieval score quality
- Measures evidence agreement between sources
- Evaluates evidence coverage of the question
- Detects contradictions between sources
- Recommends: answer, retrieve_more, or abstain

### 4. Contradiction Handler (src/evidence/)
- Detects numerical contradictions across documents
- Detects temporal contradictions
- Formats contradiction warnings for the user
- Cites both conflicting sources

### 5. Citation Validator (src/citations/)
- Validates each citation against retrieved chunks
- Checks structural validity (chunk exists)
- Checks content validity (cited text appears in chunk)
- Removes invalid citations before returning to user

### 6. Retrieval (src/retrieval/)
- Dense retrieval via vector similarity
- BM25 retrieval via lexical matching
- RRF fusion for combining signals
- Cross-encoder reranking for precision

### 7. Generation (src/generation/)
- LLM-based answer generation with strict grounding
- Citation extraction and formatting
- Support-level classification
- Abstention when evidence is insufficient

## Design Principles

1. **Modularity**: Each component replaceable independently
2. **Measurability**: Every stage records latency and metrics
3. **Traceability**: Every chunk traces to source document + page
4. **Adaptability**: System adjusts strategy per query
5. **Reliability**: Evidence checked before answer generated
6. **Reproducibility**: Config snapshots with every experiment
