# RAG Pipeline Benchmark & Experiment Framework

Comprehensive benchmark and experiment framework for evaluating Retrieval-Augmented Generation (RAG) systems on financial document question answering.

## Overview

This framework provides:

- **210 verified benchmark questions** grounded in realistic financial documents
- **8 experiment configurations** testing different retrieval strategies
- **Automated experiment execution** with raw result collection
- **Comprehensive analysis** computing retrieval, generation, and performance metrics
- **Report generation** for human-readable insights

## Quick Start

### 1. Create Document Corpus

```bash
python scripts/create_document_corpus.py
```

This creates 3 sample financial documents (Apple, Microsoft, Amazon 10-K filings) in `data/documents/`.

### 2. Run Experiments

```bash
python scripts/execute_experiments.py
```

This executes 8 experiments on the 210-question benchmark and saves raw results to `experiments/results/`.

### 3. Analyze Results

```bash
python scripts/analyze_experiments.py
```

This computes metrics (Recall@K, Precision@K, MRR, NDCG, etc.) and saves analysis to `experiments/analysis/`.

### 4. Generate Reports

```bash
python scripts/generate_reports.py
```

This creates human-readable reports in `experiments/reports/`:
- Individual experiment reports
- Comparison report across experiments
- Executive summary

## Benchmark Details

### Dataset Statistics

- **Total Questions:** 210
- **Answerable:** 208
- **Unanswerable:** 2
- **Query Types:** 11 categories
  - Numerical: 45 questions
  - Factual: 40 questions
  - Comparison: 30 questions
  - Temporal: 25 questions
  - Multi-hop: 20 questions
  - Definition: 15 questions
  - Table-based: 15 questions
  - Cross-document: 10 questions
  - Ambiguous: 5 questions
  - Adversarial: 3 questions
  - Insufficient evidence: 2 questions

- **Difficulty Distribution:**
  - Easy: 80 questions
  - Medium: 90 questions
  - Hard: 40 questions

### Document Corpus

The benchmark includes 3 sample documents:

1. **Apple 10-K 2023** (`apple_10k_2023.txt`)
   - Fiscal year ended September 30, 2023
   - Revenue: $383.3B
   - Net income: $97.0B
   - Employees: Not specified

2. **Microsoft 10-K 2023** (`microsoft_10k_2023.txt`)
   - Fiscal year ended June 30, 2023
   - Revenue: $211.9B
   - Net income: $72.4B
   - Employees: 221,000

3. **Amazon 10-K 2023** (`amazon_10k_2023.txt`)
   - Fiscal year ended December 31, 2023
   - Revenue: $574.8B
   - Net income: $30.4B
   - Employees: 1,525,000

**Note:** These are sample documents for benchmarking. For production use, download real SEC filings from [SEC EDGAR](https://www.sec.gov/edgar).

## Experiments

### Experiment Configurations

| ID | Name | Description |
|----|------|-------------|
| EXP-01 | Dense Baseline | Dense retrieval only (no BM25, no reranking) |
| EXP-02 | BM25 Baseline | BM25 retrieval only (no dense, no reranking) |
| EXP-03 | Hybrid RRF | Hybrid retrieval with RRF fusion |
| EXP-04 | Hybrid Dense-Heavy | Hybrid with 80% dense, 20% BM25 |
| EXP-05 | Hybrid Lexical-Heavy | Hybrid with 20% dense, 80% BM25 |
| EXP-06 | Adaptive Retrieval | Query-type-aware adaptive retrieval |
| EXP-07 | Hybrid + Rerank | Hybrid retrieval with cross-encoder reranking |
| EXP-08 | Adaptive + Rerank | Full system with adaptive retrieval + reranking |

### Metrics Computed

#### Retrieval Metrics
- **Recall@1, Recall@5, Recall@10**: Fraction of relevant chunks retrieved
- **Precision@5**: Fraction of retrieved chunks that are relevant
- **MRR**: Mean Reciprocal Rank
- **NDCG@5**: Normalized Discounted Cumulative Gain

#### Generation Metrics
- **Answer Correctness**: Keyword overlap with expected answer
- **Citation Precision**: Fraction of citations that are correct
- **Citation Recall**: Fraction of ground truth sources cited
- **Abstention Accuracy**: Correct abstention on unanswerable questions

#### Performance Metrics
- **Latency P50, P90, P95, P99**: Latency percentiles
- **Throughput**: Queries per second

## File Structure

```
.
├── benchmarks/
│   └── comprehensive_benchmark_200.json  # 210 verified questions
├── data/
│   ├── documents/
│   │   ├── apple_10k_2023.txt
│   │   ├── microsoft_10k_2023.txt
│   │   └── amazon_10k_2023.txt
│   └── manifest.json
├── experiments/
│   ├── results/          # Raw experiment results
│   ├── analysis/         # Computed metrics
│   └── reports/          # Human-readable reports
├── scripts/
│   ├── create_document_corpus.py
│   ├── execute_experiments.py
│   ├── analyze_experiments.py
│   └── generate_reports.py
└── src/                  # RAG pipeline implementation
```

## Usage Examples

### Run a Single Experiment

```python
from scripts.execute_experiments import ExperimentExecutor

executor = ExperimentExecutor()
questions = executor.load_benchmark("benchmarks/comprehensive_benchmark_200.json")

result = executor.run_experiment(
    experiment_id="EXP-01_dense_baseline",
    questions=questions[:10],  # Run on first 10 questions
    config_override={
        "retrieval": {
            "dense_top_k": 50,
            "bm25_top_k": 0,
            "rerank_enabled": False,
        }
    }
)

executor.save_results(result)
```

### Analyze Specific Experiment

```python
from scripts.analyze_experiments import ExperimentAnalyzer

analyzer = ExperimentAnalyzer()
analysis = analyzer.analyze_experiment("EXP-01_dense_baseline")

print(f"Recall@5: {analysis['retrieval_metrics']['recall_at_5']:.4f}")
print(f"MRR: {analysis['retrieval_metrics']['mrr']:.4f}")
```

### Compare Experiments

```python
from scripts.analyze_experiments import ExperimentAnalyzer

analyzer = ExperimentAnalyzer()
comparison = analyzer.compare_experiments([
    "EXP-01_dense_baseline",
    "EXP-03_hybrid_rrf",
    "EXP-06_adaptive_retrieval"
])

print(f"Best Recall@5: {comparison['comparison']['retrieval_metrics.recall_at_5']}")
```

## Extending the Benchmark

### Add New Questions

Edit `benchmarks/comprehensive_benchmark_200.json` and add questions in this format:

```json
{
  "question_id": "Q211",
  "question": "What was the company's operating income?",
  "expected_answer": "The company's operating income was $88.5 billion.",
  "acceptable_answers": ["$88.5 billion", "88.5 billion"],
  "source_document": "microsoft_10k_2023.txt",
  "source_section": "Operating Income",
  "evidence_span": "Operating income increased 12% to $88.5 billion",
  "query_type": "numerical",
  "difficulty": "easy",
  "answerable": true,
  "relevant_chunk_ids": ["chunk_msft_013"]
}
```

### Add New Documents

1. Add document to `data/documents/`
2. Update `data/manifest.json` with metadata
3. Create questions referencing the new document

### Add New Experiments

Edit `scripts/execute_experiments.py` and add to the `experiments` list:

```python
{
    "id": "EXP-09_custom",
    "description": "Custom experiment",
    "config": {
        "retrieval": {
            "dense_top_k": 100,
            "bm25_top_k": 100,
            "fusion_method": "weighted",
            "dense_weight": 0.7,
            "bm25_weight": 0.3,
            "rerank_enabled": True,
        }
    }
}
```

## Production Use

For production use with real financial documents:

1. **Download SEC Filings**
   ```bash
   # Download from SEC EDGAR
   # https://www.sec.gov/edgar/searchedgar/companysearch.html
   ```

2. **Update Manifest**
   ```python
   # Update data/manifest.json with real document metadata
   ```

3. **Expand Benchmark**
   ```bash
   # Add 500+ questions covering real documents
   ```

4. **Run Full Evaluation**
   ```bash
   python scripts/execute_experiments.py
   python scripts/analyze_experiments.py
   python scripts/generate_reports.py
   ```

## Limitations

- **Sample Documents**: Uses sample documents, not real SEC filings
- **Simple Evaluation**: Answer correctness uses keyword overlap, not semantic evaluation
- **Limited Scope**: 210 questions, 3 documents
- **No LLM-as-Judge**: No semantic answer evaluation

## Next Steps

1. Download real SEC filings from EDGAR
2. Expand benchmark to 500+ questions
3. Implement LLM-as-judge for semantic evaluation
4. Add multi-hop and temporal reasoning tests
5. Conduct user study for real-world validation

## Citation

If you use this benchmark in your research, please cite:

```bibtex
@software{rag_pipeline_benchmark_2024,
  title = {RAG Pipeline Benchmark: Financial Document QA},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/your-repo/rag-pipeline}
}
```

## License

MIT License - See LICENSE file for details.

## Contact

For questions or issues, please open an issue on GitHub.
