# Project Audit — RAG Pipeline

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
