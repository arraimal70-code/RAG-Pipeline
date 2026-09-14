# Experiment Suite

## Overview

19 experiments + ablation studies designed to systematically investigate each component's contribution to retrieval quality, factual reliability, latency, and cost.

## Experiment List

### Retrieval Strategy Experiments

| ID | Name | Hypothesis | Variables |
|----|------|-----------|-----------|
| EXP-01 | Dense Baseline | Dense retrieval alone provides reasonable baseline | dense_top_k=50, bm25=disabled |
| EXP-02 | BM25 Baseline | BM25 alone provides strong lexical retrieval | bm25_top_k=50, dense=disabled |
| EXP-03 | Hybrid RRF | Hybrid (dense+BM25+RRF) outperforms either alone | dense=50, bm25=50, fusion=RRF |
| EXP-04 | Dense-Heavy | Dense-heavy weighting improves conceptual queries | dense_weight=0.8, bm25_weight=0.2 |
| EXP-05 | Lexical-Heavy | Lexical-heavy improves exact-match queries | dense_weight=0.2, bm25_weight=0.8 |
| EXP-06 | Adaptive | Query-type-aware weights outperform fixed hybrid | adaptive_enabled=true |

### Chunking Experiments

| ID | Name | Hypothesis | Variables |
|----|------|-----------|-----------|
| EXP-07a | Fixed Chunking | Fixed-size provides predictable but suboptimal retrieval | strategy=fixed, size=512 |
| EXP-07b | Sentence Chunking | Sentence-based preserves semantic boundaries | strategy=sentence |
| EXP-07c | Recursive Chunking | Recursive balances structure and flexibility | strategy=recursive |
| EXP-07d | Structure Chunking | Structure-aware produces topically coherent chunks | strategy=structure |

### Component Impact Experiments

| ID | Name | Hypothesis | Variables |
|----|------|-----------|-----------|
| EXP-09a | With Reranking | Cross-encoder reranking improves precision | rerank_enabled=true |
| EXP-09b | Without Reranking | Without reranking, precision drops but latency improves | rerank_enabled=false |
| EXP-10a | Top-K=3 | Smaller top-K reduces latency | rerank_top_k=3 |
| EXP-10b | Top-K=5 | Default top-K | rerank_top_k=5 |
| EXP-10c | Top-K=10 | Larger top-K improves recall | rerank_top_k=10 |

### Reliability Experiments

| ID | Name | Hypothesis | Variables |
|----|------|-----------|-----------|
| EXP-11 | Evidence Sufficiency | Evidence checking reduces hallucination | sufficiency_enabled=true |
| EXP-12 | Citation Validation | Validating citations improves trustworthiness | citation_validation=enabled |
| EXP-13 | Contradiction Detection | Contradiction detection flags conflicting sources | contradiction_detection=enabled |

### Ablation Studies

| ID | Name | What's Removed | Purpose |
|----|------|---------------|---------|
| EXP-ABL-1 | No BM25 | BM25 retrieval | Does lexical retrieval add value? |
| EXP-ABL-2 | No Dense | Dense retrieval | Does semantic retrieval add value? |
| EXP-ABL-3 | No Adaptive | Adaptive routing | Does query classification help? |
| EXP-ABL-4 | No Evidence Check | Evidence sufficiency | Does evidence checking reduce hallucination? |
| EXP-ABL-5 | No Reranker | Cross-encoder reranking | Does reranking justify its cost? |
| EXP-ABL-6 | No Citation Validation | Citation validation | Does validation catch real errors? |

### Full Pipeline

| ID | Name | Description |
|----|------|-------------|
| EXP-19 | Full Optimized | All components enabled with best configurations |

## Running Experiments

```bash
# Run all experiments
python experiments/runner.py

# Run specific experiment
python -c "
from experiments.runner import ExperimentRunner, EXPERIMENTS
runner = ExperimentRunner()
questions = runner.load_benchmark()
result = runner.run_experiment('EXP-03_hybrid_rrf', EXPERIMENTS['EXP-03_hybrid_rrf'], questions)
"
```

## Expected Output

Each experiment produces:
1. JSON result file in `experiments/results/`
2. Console output with metrics
3. Entry in `experiments/results/COMPARISON.md`

## Status

**ALL EXPERIMENTS PENDING** — Require real documents and API access to execute.
