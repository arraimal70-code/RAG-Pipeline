export interface DocFile {
  title: string;
  path: string;
  icon: string;
  category: string;
  content: string;
}

export const documentation: DocFile[] = [
  {
    title: "Project Audit",
    path: "docs/PROJECT_AUDIT.md",
    icon: "🔍",
    category: "Audit",
    content: `# Project Audit — RAG Pipeline

## Current State

The initial repository contained a basic two-stage RAG pipeline:
- ingest.py: Load PDFs → chunk → embed → store in Chroma
- query.py: Retrieve → prompt → generate → cite
- config.py: Basic configuration constants

## Major Weaknesses

### Critical
- **No evaluation framework** — cannot measure retrieval or generation quality
- **No benchmark dataset** — no ground truth for comparison
- **Zero tests** — no unit, integration, or failure tests
- **Only dense retrieval** — no BM25, no hybrid, no reranking
- **No abstention** — system always attempts an answer, even when evidence is insufficient

### High
- **Single chunking strategy** — cannot determine optimal approach experimentally
- **No citation validation** — citations not verified against source
- **No hallucination detection** — unsupported answers presented confidently
- **No security hardening** — no input validation, no prompt injection protection
- **No Docker/CI** — no reproducible environment or automated testing

### Medium
- **No adaptive retrieval** — all queries use identical strategy
- **No contradiction handling** — conflicting sources silently resolved
- **No experiment tracking** — cannot reproduce or compare configurations
- **No failure analysis** — failures not categorized or learned from

## Recommended Architecture

Transform into a modular, component-based system with:
1. Clean interfaces between stages (Pydantic models)
2. Multiple retrieval strategies (dense + BM25 + hybrid + rerank)
3. Adaptive retrieval based on query analysis
4. Evidence sufficiency assessment before generation
5. Citation validation against retrieved evidence
6. Comprehensive evaluation framework
7. Experiment runner with hypothesis/method/result structure
8. Full test suite (unit + integration + failure)
9. Security hardening (input validation, injection detection)
10. Docker + CI/CD for reproducibility

## Implementation Roadmap

| Phase | Component | Priority | Status |
|-------|-----------|----------|--------|
| 1 | Core models & config | P0 | ✅ Implemented |
| 2 | Robust PDF parser | P0 | ✅ Implemented |
| 3 | Multiple chunking strategies | P0 | ✅ Implemented |
| 4 | BM25 index | P0 | ✅ Implemented |
| 5 | Hybrid retrieval + RRF | P0 | ✅ Implemented |
| 6 | Cross-encoder reranking | P1 | ✅ Implemented |
| 7 | Query analysis + adaptive retrieval | P1 | ✅ Implemented |
| 8 | Evidence sufficiency + abstention | P1 | ✅ Implemented |
| 9 | Contradiction detection | P1 | ✅ Implemented |
| 10 | Citation validation | P1 | ✅ Implemented |
| 11 | Evaluation framework | P0 | ✅ Implemented |
| 12 | Benchmark dataset | P0 | ✅ Template created |
| 13 | Experiment runner | P1 | ✅ Implemented |
| 14 | Testing suite | P0 | ✅ Implemented |
| 15 | Security hardening | P1 | ✅ Implemented |
| 16 | API layer | P1 | ✅ Implemented |
| 17 | Docker + CI | P2 | ✅ Implemented |
| 18 | Documentation | P1 | ✅ Implemented |
`
  },

  {
    title: "Architecture",
    path: "docs/ARCHITECTURE.md",
    icon: "🏗️",
    category: "Design",
    content: `# System Architecture

## Overview

The RAG Pipeline follows an adaptive, evidence-aware architecture. Unlike basic RAG systems that use a fixed retrieve-then-generate pipeline, this system dynamically adjusts its retrieval strategy based on query characteristics and assesses evidence sufficiency before generating answers.

## Central Research Question

> How can a RAG system dynamically balance retrieval quality, factual reliability, latency, and computational cost while recognizing when available evidence is insufficient to answer a question?

## Data Flow

\`\`\`
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
\`\`\`

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
`
  },

  {
    title: "Research Report",
    path: "docs/RESEARCH_REPORT.md",
    icon: "📊",
    category: "Research",
    content: `# Research Report: Evidence-Aware Adaptive RAG

## 1. Abstract

This project investigates how retrieval strategy, chunking, reranking, adaptive weighting, and abstention mechanisms affect factual reliability, citation accuracy, latency, and cost in document-grounded question answering. We build infrastructure to measure these effects systematically. **Results are pending** — the framework is complete but experiments require document ingestion and API access.

## 2. Problem

LLMs hallucinate when asked about specific documents. RAG addresses this by retrieving context before generation. However, RAG quality depends on retrieval strategy, chunking, and whether the system can refuse to answer. These factors are rarely studied together.

## 3. Research Question

> How can a RAG system dynamically balance retrieval quality, factual reliability, latency, and computational cost while recognizing when available evidence is insufficient?

## 4. Hypotheses

- H1: Hybrid retrieval (dense + BM25) outperforms either alone
- H2: Cross-encoder reranking improves citation accuracy
- H3: Adaptive weighting (query-type-aware) improves retrieval over fixed weights
- H4: Evidence sufficiency assessment reduces hallucination
- H5: Structure-aware chunking produces better retrieval than fixed-size

## 5. System Architecture

See docs/ARCHITECTURE.md. Key innovations:
- Query analysis → adaptive retrieval weights
- Evidence sufficiency check before generation
- Contradiction detection across sources
- Citation validation against retrieved evidence

## 6. Retrieval Methods

- **Dense**: Cosine similarity via sentence-transformers
- **BM25**: Lexical matching via rank_bm25
- **Hybrid**: Weighted fusion with query-type-adaptive weights
- **RRF**: Reciprocal Rank Fusion as alternative
- **Reranking**: Cross-encoder (ms-marco-MiniLM)

## 7. Dataset

Benchmark dataset with 15 question categories:
direct_lookup, multi_hop, numerical, definition, comparison, summarization, cross_section, cross_document, ambiguous, unanswerable, adversarial, table_based, contradictory, temporal, long_context

Target: 100-300 verified questions. Template provided.

## 8. Experimental Methodology

19 experiments (EXP-01 through EXP-19) plus ablation studies.
Each experiment records: hypothesis, method, config snapshot, metrics, latency, errors.

## 9. Metrics

**Retrieval**: Recall@K, MRR, nDCG, source accuracy, passage accuracy
**Generation**: Factual correctness, groundedness, citation accuracy, hallucination rate
**System**: Latency (p50, p95), token usage, cost
**Abstention**: Correct refusal rate, false answering rate

## 10. Results

> **STATUS: RESULTS PENDING**

The experiment infrastructure is complete. Results will be populated when experiments are executed with actual documents and API access. Per the project's core rules, no results are fabricated.

## 11. Ablation Studies

| Comparison | Tests |
|-----------|-------|
| EXP-03 vs EXP-ABL_no_bm25 | Does BM25 add value? |
| EXP-03 vs EXP-ABL_no_dense | Does dense add value? |
| EXP-06 vs EXP-ABL_no_adaptive | Does adaptive weighting help? |
| EXP-19 vs EXP-ABL_no_evidence_check | Does evidence checking reduce hallucination? |

## 12. Failure Analysis

See docs/FAILURE_ANALYSIS.md. 15 failure categories defined.
Every failed question is preserved with: question, evidence, answer, category, cause, mitigation.

## 13. Security

See docs/SECURITY.md. Protections: input validation, prompt injection detection, resource limits, secrets management, non-root Docker.

## 14. Limitations

1. Evaluation uses heuristics — proper evaluation requires LLM judge or human annotation
2. Dataset is template — needs verified ground truth
3. Only one embedding model tested by default
4. Only GPT-4o-mini tested for generation
5. PDF-only — no other document formats
6. No OCR for scanned documents
7. Contradiction detection is heuristic-based

## 15. Future Work

1. LLM-as-judge evaluation
2. Multi-format document support
3. OCR integration
4. Adaptive chunking (learn optimal size from data)
5. Query expansion (HyDE, multi-query)
6. Conversation memory
7. Table extraction
8. Graph-based retrieval for multi-hop

## 16. Conclusion

This project provides infrastructure to systematically study RAG pipeline components. The key contribution is the experimental framework that enables evidence-based architectural decisions. The system is designed to answer: "Which components materially improve reliability, and at what cost?"
`
  },

  {
    title: "Failure Analysis",
    path: "docs/FAILURE_ANALYSIS.md",
    icon: "🔬",
    category: "Analysis",
    content: `# Failure Analysis Framework

## Overview

Every RAG system will fail. The question is whether we can detect, categorize, and learn from failures. This document defines a 15-category failure taxonomy.

## Failure Taxonomy

### 1. Retrieval Failure
Correct evidence exists in the index but was not retrieved.
**Detection**: Recall@K metrics. **Mitigation**: Increase top-K, add BM25.

### 2. Chunking Failure
Relevant information split across chunks making it unretrievable.
**Detection**: Compare chunking strategies. **Mitigation**: Increase overlap, use structure-aware.

### 3. Embedding Failure
Query and relevant text have low semantic similarity despite being related.
**Detection**: Low dense retrieval scores for relevant content. **Mitigation**: Try different embedding model.

### 4. Ranking Failure
Relevant chunks retrieved but ranked below irrelevant ones.
**Detection**: nDCG metrics. **Mitigation**: Add reranking, tune fusion weights.

### 5. Context Window Failure
Too much context overwhelms the LLM, causing it to ignore relevant evidence.
**Detection**: Correct retrieval but wrong answer. **Mitigation**: Reduce context size, better chunk selection.

### 6. Generation Failure
Evidence retrieved correctly but LLM produced incorrect answer.
**Detection**: Compare answer to expected. **Mitigation**: Better prompt engineering, lower temperature.

### 7. Citation Failure
Answer correct but citations don't point to actual evidence.
**Detection**: Citation validation. **Mitigation**: Structured citation format, post-validation.

### 8. Hallucination
Answer contains information not in any retrieved evidence.
**Detection**: Support level = UNSUPPORTED. **Mitigation**: Stronger grounding, abstention.

### 9. Parsing Failure
PDF text extraction produced incorrect or incomplete text.
**Detection**: Compare extracted text to visual inspection. **Mitigation**: Alternative parsers, OCR.

### 10. OCR Failure
Scanned document text not recognized.
**Detection**: Empty or garbled pages. **Mitigation**: Better OCR engine.

### 11. Table Understanding Failure
Tabular data not correctly interpreted.
**Detection**: Numerical answers wrong for table-based questions. **Mitigation**: Table extraction.

### 12. Contradictory Source Failure
Different documents contain contradictory information.
**Detection**: Contradiction detection module. **Mitigation**: Flag contradictions, cite both sources.

### 13. Unanswerable Question Failure
System should have refused but answered anyway.
**Detection**: Unanswerable benchmark questions that receive answers. **Mitigation**: Evidence sufficiency check.

### 14. Latency/Resource Failure
System exceeds acceptable response time or resource limits.
**Detection**: p95 latency monitoring. **Mitigation**: Caching, batching, smaller models.

### 15. Prompt Injection Failure
Malicious content in documents or queries manipulates the system.
**Detection**: Adversarial benchmark questions. **Mitigation**: Input sanitization, system prompt hardening.

## Retrieval vs Generation Failure Decomposition

Critical distinction:
- **Retrieval failure**: Correct evidence exists but wasn't retrieved
- **Generation failure**: Evidence was retrieved but answer is wrong
- **Citation failure**: Answer is correct but citations are wrong
- **Evidence failure**: Evidence itself is conflicting or insufficient

This decomposition appears in the evaluation framework.

## Failure Log Format

\`\`\`json
{
  "question_id": "q042",
  "question": "...",
  "expected_answer": "...",
  "generated_answer": "...",
  "failure_category": "retrieval_failure",
  "root_cause": "Relevant chunk ranked 15th, outside top-5",
  "retrieved_evidence": [...],
  "mitigation": "Increase rerank_top_k from 5 to 10",
  "mitigation_worked": null
}
\`\`\`
`
  },

  {
    title: "Security",
    path: "docs/SECURITY.md",
    icon: "🔒",
    category: "Security",
    content: `# Security Considerations

## Threat Model

The RAG pipeline processes untrusted input at multiple stages:
1. Uploaded documents — may contain malicious content
2. Extracted text — may contain prompt injection
3. User queries — may attempt system manipulation
4. LLM responses — may be manipulated by injected instructions

## Protections

### Input Validation
- File type: Only .pdf accepted
- File size: Max 50MB
- Page count: Max 500 pages
- Content hash: SHA-256 for deduplication
- Path traversal: Sanitized via pathlib

### Prompt Injection Defense
- Retrieved text treated as untrusted
- System prompt instructs LLM to ignore context instructions
- Retrieved chunks clearly delimited
- Max chunk length: 10,000 characters
- Injection pattern detection in retrieved text

### Resource Protection
- Max file size prevents disk exhaustion
- Max page count prevents memory exhaustion
- Max chunk size prevents prompt overflow
- Batch size limits prevent API rate limiting

### Secrets Management
- API keys in .env (never committed)
- .env in .gitignore
- .env.example without real values
- No secrets in logs or error messages

### Execution Security
- Docker runs as non-root user
- No shell injection in file handling
- Path operations use pathlib

## Security Checklist
- [x] .env.example provided
- [x] .env in .gitignore
- [x] File type validation
- [x] File size limits
- [x] No secrets in logs
- [x] Non-root Docker user
- [x] Input validation on API
- [x] Prompt injection awareness

## Known Limitations
1. No malware scanning for uploads
2. No authentication (suitable for local/research)
3. No rate limiting
4. Prompt injection defense is probabilistic
5. No encryption at rest for vector store
`
  },

  {
    title: "Decisions",
    path: "docs/DECISIONS.md",
    icon: "🧠",
    category: "Design",
    content: `# Engineering Decision Records

## ADR-001: ChromaDB over FAISS
**Decision**: ChromaDB as primary vector store.
**Alternatives**: FAISS (faster, no persistence), Pinecone (managed, paid), Weaviate (heavy).
**Rationale**: Built-in persistence, metadata filtering, simple API, free, local.
**Tradeoff**: Slower than FAISS at scale. Acceptable for research.

## ADR-002: BM25 alongside dense retrieval
**Decision**: Both dense and BM25 retrieval.
**Rationale**: Dense fails on exact matches (names, numbers). BM25 fails on semantic similarity. Hybrid combines both.
**Evidence**: IR literature consistently shows hybrid > either alone.

## ADR-003: Reciprocal Rank Fusion
**Decision**: RRF for combining retrieval results.
**Alternatives**: Weighted score fusion (needs normalization), Learning-to-rank (needs training data).
**Rationale**: Parameter-free, robust to score scale differences, well-documented (Cormack et al., 2009).

## ADR-004: Cross-encoder reranking
**Decision**: Cross-encoder (ms-marco-MiniLM) as reranker.
**Rationale**: Bi-encoders fast but less accurate. Cross-encoders process query+document together. Reranking 20 candidates is fast enough.
**Tradeoff**: ~50ms additional latency for improved precision.

## ADR-005: all-MiniLM-L6-v2 as default embedding
**Decision**: Default to local sentence-transformers model.
**Alternatives**: OpenAI (better, costs money), BGE-large (better, slower).
**Rationale**: Free, fast, small (80MB), good enough quality, works offline.

## ADR-006: Multiple chunking strategies
**Decision**: 4 strategies (fixed, sentence, recursive, structure-aware).
**Rationale**: Different document types benefit from different strategies. No single strategy is universally best.

## ADR-007: Abstention over always answering
**Decision**: Explicit abstention when evidence is insufficient.
**Rationale**: Cost of wrong answer > cost of no answer. System classifies: SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED, INSUFFICIENT_EVIDENCE.

## ADR-008: Rule-based query classification
**Decision**: Rule-based (not LLM-based) query classification.
**Alternatives**: LLM classifier (adds latency, cost, noise).
**Rationale**: Fast, deterministic, debuggable. Sufficient for the granularity needed.

## ADR-009: Evidence sufficiency before generation
**Decision**: Assess evidence quality before generating answer.
**Rationale**: Prevents hallucination by checking retrieval scores, agreement, coverage, and contradictions before LLM invocation.

## ADR-010: Pydantic models for data flow
**Decision**: Pydantic models for all inter-component data.
**Rationale**: Type safety, validation, serialization, documentation, IDE support.
`
  },

  {
    title: "Reproducibility",
    path: "docs/REPRODUCIBILITY.md",
    icon: "🔄",
    category: "Operations",
    content: `# Reproducibility Guide

## Setup
\`\`\`bash
git clone https://github.com/arraimal70-code/RAG-Pipeline.git
cd RAG-Pipeline
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add OPENAI_API_KEY
\`\`\`

## Running Experiments
\`\`\`bash
# 1. Add documents
mkdir -p data/documents && cp *.pdf data/documents/

# 2. Ingest
python -m src.pipeline ingest

# 3. Run experiments
python experiments/runner.py

# 4. View results
cat experiments/results/COMPARISON.md
\`\`\`

## Docker
\`\`\`bash
docker build -t rag-pipeline .
docker run -p 8000:8000 --env-file .env rag-pipeline
\`\`\`

## Result Format
Each experiment produces JSON with:
- experiment_id, name, hypothesis, method
- config_snapshot (full configuration at time of run)
- dataset_version, timestamp
- metrics (aggregate)
- question_results (per-question detail)
- total_latency_ms, total_tokens, estimated_cost
- errors, interpretation, limitations

## Version Pinning
requirements.txt pins exact versions for reproducibility.

## Random Seeds
\`\`\`python
import numpy as np
np.random.seed(42)
\`\`\`
Note: LLM outputs are inherently non-deterministic even at temperature=0.
`
  },

  {
    title: "Real-World Case Study",
    path: "docs/REAL_WORLD_CASE_STUDY.md",
    icon: "📋",
    category: "Case Study",
    content: `# Real-World Case Study: Financial Document Intelligence

## Problem

Financial analysts spend hours searching through quarterly reports, annual filings, and research notes to find specific data points, compare performance across periods, and verify claims. This is time-consuming, error-prone, and does not scale.

## Current Difficulty

- Manual search through hundreds of pages
- Difficulty finding specific numbers in tables
- Hard to compare data across documents
- Risk of misquoting or misattributing data
- No way to verify claims against source documents quickly

## Proposed RAG Solution

A document-grounded QA system that:
1. Ingests financial PDFs (quarterly reports, annual filings)
2. Allows natural-language questions about financial data
3. Returns answers with page-level citations
4. Flags contradictions between documents
5. Refuses to answer when evidence is insufficient

## System Architecture

- **Parsing**: PyMuPDF with structure detection for financial tables
- **Chunking**: Structure-aware (sections, tables, footnotes)
- **Retrieval**: Adaptive hybrid (BM25-heavy for numerical queries)
- **Generation**: GPT-4o-mini with strict grounding
- **Citations**: Validated against retrieved chunks
- **Contradictions**: Detected across documents (e.g., different revenue figures)

## Evaluation

### Benchmark Construction
- 50+ questions across financial documents
- Categories: numerical lookup, comparison, temporal, cross-document
- Unanswerable questions (data not in documents)
- Adversarial questions (prompt injection attempts)

### Metrics
- Retrieval: Recall@5 for financial data points
- Generation: Numerical accuracy (exact match for numbers)
- Citation: Page-level accuracy
- Abstention: Correct refusal on unanswerable questions

## Measured Improvement

> **RESULTS PENDING** — Requires actual financial documents and API access.

The infrastructure is complete. When executed, the system will measure:
- Time saved per query vs. manual search
- Retrieval accuracy for numerical data
- Citation accuracy (page-level)
- Hallucination rate for financial claims
- Abstention accuracy

## Failure Cases (Anticipated)

1. **Table extraction**: Financial tables may not parse correctly
2. **Numerical precision**: LLM may round or misread numbers
3. **Cross-reference**: Comparing data across documents requires multi-hop
4. **Temporal reasoning**: "How did X change from Q1 to Q2?" requires temporal retrieval
5. **Abbreviations**: Financial jargon may not match embedding vocabulary

## Limitations

1. Only handles PDF format
2. No OCR for scanned financial documents
3. Table extraction is heuristic-based
4. Numerical accuracy depends on LLM capability
5. Does not perform calculations (only retrieves stated numbers)
6. Requires API access for LLM generation

## Practical Usefulness

Even with limitations, the system can:
- Quickly locate specific data points in large reports
- Verify claims against source documents
- Flag contradictions between different reports
- Reduce time spent on manual document search
- Provide auditable citations for every answer
`
  },

  {
    title: "Research Log",
    path: "docs/RESEARCH_LOG.md",
    icon: "📝",
    category: "Research",
    content: `# Research Log

This document records the evolution of experimental findings.

---

## Entry 1: Initial Architecture Decision

### Hypothesis
Hybrid retrieval (dense + BM25) will outperform either method alone for financial document QA.

### Experiment
EXP-01 (dense only) vs EXP-02 (BM25 only) vs EXP-03 (hybrid RRF)

### Result
**RESULTS PENDING**

### Interpretation
Expected: Hybrid will excel on both exact-match queries (via BM25) and conceptual queries (via dense). Pure dense will struggle with specific financial terms. Pure BM25 will miss semantically similar but lexically different passages.

### Next Experiment
If hybrid wins, test whether adaptive weighting (EXP-06) improves further.

---

## Entry 2: Adaptive Retrieval

### Hypothesis
Query-type-aware adaptive weighting will improve retrieval over fixed 50/50 hybrid.

### Experiment
EXP-03 (fixed hybrid) vs EXP-06 (adaptive hybrid)

### Result
**RESULTS PENDING**

### Interpretation
Expected: Adaptive will help most on exact queries (where BM25 should dominate) and conceptual queries (where dense should dominate). The benefit may be small if the dataset is mostly one type.

### Failure Mode
If adaptive performs worse, it may be because:
- Query classifier is inaccurate
- Weight differences are too small to matter
- The dataset doesn't have enough variety in query types

---

## Entry 3: Evidence Sufficiency

### Hypothesis
Evidence sufficiency assessment will reduce hallucination without excessive false refusals.

### Experiment
EXP-19 (full pipeline with evidence check) vs EXP-ABL_no_evidence_check

### Result
**RESULTS PENDING**

### Interpretation
Expected: Hallucination rate should decrease. Abstention rate should increase. The question is whether the increase in correct abstentions outweighs the increase in false refusals.

### Key Metric
F1 score of abstention decisions (harmonic mean of correct abstention rate and correct answer rate).

---

## Entry 4: Reranking Impact

### Hypothesis
Cross-encoder reranking will significantly improve precision at the cost of ~50ms latency.

### Experiment
EXP-09_full_with_rerank vs EXP-09_full_no_rerank

### Result
**RESULTS PENDING**

### Interpretation
Expected: Precision@5 should improve substantially. The question is whether the latency cost is acceptable for the quality improvement.

---

*This log will be updated as experiments are executed and results become available.*
`
  },

  {
    title: "Final Review",
    path: "docs/FINAL_REVIEW.md",
    icon: "✅",
    category: "Audit",
    content: `# Final Review — Brutally Honest Assessment

## 1. What did we actually build?

A modular, evidence-aware RAG pipeline with:
- Multiple retrieval strategies (dense, BM25, hybrid, reranked)
- Adaptive retrieval based on query classification
- Evidence sufficiency assessment before generation
- Contradiction detection across sources
- Citation validation against retrieved evidence
- Comprehensive evaluation framework
- Experiment runner with 19+ experiments
- 15-category failure taxonomy
- Full test suite
- Docker + CI/CD

## 2. What is technically difficult about it?

- Implementing adaptive retrieval that actually improves over fixed weights (unproven)
- Evidence sufficiency assessment that balances coverage vs. false refusal
- Contradiction detection without expensive NLI models
- Citation validation that catches real errors without false positives
- Building a benchmark dataset with verified ground truth

## 3. What is genuinely original?

- The combination of adaptive retrieval + evidence sufficiency + contradiction detection in a single evaluable framework
- The experimental methodology for measuring which components matter
- The 15-category failure taxonomy applied to RAG
- The cost-quality frontier analysis approach

## 4. What did we experimentally prove?

**NOTHING YET.** Results are pending. The infrastructure is complete but experiments have not been executed with real data.

## 5. What did we fail to prove?

Everything. No experiments have been run. All hypotheses are untested.

## 6. What are the biggest weaknesses?

1. **No experimental results** — the entire research contribution is unvalidated
2. **Benchmark is a template** — needs real verified questions
3. **Evaluation is heuristic** — factual correctness uses support-level as proxy
4. **Single embedding model** — only MiniLM tested by default
5. **Single LLM** — only GPT-4o-mini tested
6. **PDF-only** — no other document formats
7. **No OCR** — scanned documents not handled
8. **Contradiction detection is heuristic** — may miss subtle contradictions

## 7. Where does the system fail?

- Table extraction from financial documents
- Numerical precision (LLM may round numbers)
- Cross-document reasoning for complex multi-hop
- Adversarial content in documents
- Very long documents (>500 pages)
- Queries requiring domain-specific knowledge not in embeddings

## 8. Scalability limitations?

- ChromaDB works for <1M vectors but degrades beyond that
- BM25 index is in-memory — large corpora need disk-based approach
- Reranking adds ~50ms per query — at scale, need batch processing
- No distributed indexing or retrieval
- No caching layer for repeated queries

## 9. Security limitations?

- No malware scanning for PDFs
- No authentication on API
- No rate limiting
- Prompt injection defense is probabilistic
- No encryption at rest

## 10. Research limitations?

- No statistical analysis (confidence intervals, significance tests)
- No human evaluation of answer quality
- No comparison with existing RAG systems
- No ablation of individual components with statistical evidence
- Dataset construction methodology not validated by multiple annotators

## 11. What would an expert criticize?

- "You claim adaptive retrieval helps but have no results"
- "Your evaluation metrics are all heuristic proxies"
- "Your benchmark is a template, not a real dataset"
- "You haven't compared against any baseline RAG system"
- "Your contradiction detection is too simplistic"
- "You haven't measured inter-annotator agreement on your benchmark"

## 12. What should be improved next?

1. Execute experiments and populate results
2. Build real benchmark with verified ground truth
3. Add LLM-as-judge evaluation
4. Add statistical analysis (bootstrap confidence intervals)
5. Compare against existing RAG systems (RAGAS, ARES)
6. Improve contradiction detection with NLI models
7. Add multi-format document support
8. Add caching and performance optimization

## Ratings (honest)

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Technical Strength | 7/10 | Solid architecture, unvalidated claims |
| Research Strength | 4/10 | Good framework, no results |
| Engineering Strength | 8/10 | Clean code, good tests, modular |
| Reliability | 6/10 | Abstention + validation, but untested |
| Originality | 6/10 | Good combination of ideas, not groundbreaking |
| Real-world Usefulness | 5/10 | Useful concept, needs validation |
| Reproducibility | 8/10 | Docker, pinned deps, config snapshots |
| Remaining Weaknesses | Significant | No results, heuristic evaluation, template dataset |

## Overall

This is a well-engineered framework for studying RAG systems. The architecture is sound, the code is clean, and the experimental methodology is rigorous. However, **the project's central claim — that adaptive retrieval and evidence sufficiency improve reliability — is completely unvalidated.** Until experiments are executed and results are populated, this is a promising infrastructure, not a research contribution.
`
  },
];
