# Experiment Results

> **STATUS: RESULTS PENDING** — No experiments have been executed yet.

## How to Generate Results

```bash
# 1. Add financial documents
mkdir -p data/documents
cp /path/to/sec_filings/*.pdf data/documents/

# 2. Ingest documents
python -m src.pipeline ingest

# 3. Run experiments
python experiments/runner.py

# 4. View results
cat experiments/results/COMPARISON.md
```

## Experiment Configuration

Each experiment records:
- Experiment ID and name
- Hypothesis being tested
- Configuration snapshot (all parameters)
- Dataset version
- Timestamp
- Per-question results
- Aggregate metrics
- Latency breakdown
- Token usage and estimated cost
- Errors encountered

## Metrics Tracked

### Retrieval Metrics
- Recall@1, Recall@3, Recall@5, Recall@10
- MRR (Mean Reciprocal Rank)
- nDCG@5
- Source retrieval accuracy
- Passage retrieval accuracy

### Generation Metrics
- Factual correctness (heuristic)
- Groundedness
- Citation precision
- Citation recall
- Hallucination rate
- Claim-level faithfulness

### System Metrics
- End-to-end latency (p50, p95)
- Per-stage latency breakdown
- Token usage
- Estimated cost per query

### Abstention Metrics
- Correct abstention rate
- False abstention rate
- Unsupported answer rate

## Results Format

Results are stored as JSON in `experiments/results/`:

```json
{
  "experiment_id": "uuid",
  "name": "EXP-03_hybrid_rrf",
  "hypothesis": "Hybrid retrieval outperforms either alone",
  "config_snapshot": {...},
  "metrics": {
    "recall@5": 0.72,
    "mrr": 0.68,
    "factual_correctness": 0.81,
    ...
  },
  "question_results": [...],
  "total_latency_ms": 45230,
  "errors": []
}
```

## Comparison Table

After running experiments, a comparison table will be auto-generated in `experiments/results/COMPARISON.md`.

---

*This document will be populated with actual results after experiments are executed.*
