# Empirical Benchmarking Suite & Adversarial Evaluation

## 1. Overview
This document specifies the quantitative benchmarking suite, evaluation methodology, and empirical performance metrics for the **Tier-1 Evidence-Aware RAG Pipeline**.

The evaluation harness evaluates:
1. Standard progressive retrieval ablation (`benchmarks/compare_strategies.py`)
2. Multi-hop and multi-document evaluation (`benchmarks/run_benchmark.py`)
3. **Adversarial SEC Form 10-K Benchmark Suite** (`benchmarks/run_adversarial_eval.py`)

---

## 2. Evaluation Metrics Formalism

### Retrieval Metrics
- **Hit@K** ($K \in \{1, 3, 5\}$):
  $$\text{Hit@K} = \frac{1}{|Q|} \sum_{q \in Q} \mathbb{I}\left( \text{Gold}(q) \cap \text{TopK}(q) \neq \emptyset \right)$$
- **Mean Reciprocal Rank (MRR@5)**:
  $$\text{MRR@5} = \frac{1}{|Q|} \sum_{i=1}^{|Q|} \frac{1}{\text{rank}_i}$$
- **Normalized Discounted Cumulative Gain (NDCG@5)**:
  $$\text{DCG@5} = \sum_{i=1}^{5} \frac{2^{\text{rel}_i} - 1}{\log_2(i + 1)}, \quad \text{NDCG@5} = \frac{\text{DCG@5}}{\text{IDCG@5}}$$

### Grounding & NLI Entailment Metrics
- **NLI Claim Entailment Rate**: Fraction of generated atomic claims classified as `ENTAILMENT` by the NLI premise-hypothesis engine.
- **Hallucination Contradiction Rate**: Fraction of claims classified as `CONTRADICTION`.
- **Principled Abstention Accuracy**: Precision in returning `INSUFFICIENT_EVIDENCE` on unanswerable and out-of-scope queries.

---

## 3. Adversarial SEC Form 10-K Benchmark Results

Evaluated over real-world multi-period SEC Form 10-K disclosures containing complex multi-column operating statement matrices, segment margin tables, and non-GAAP footnotes (`data/adversarial_sec_10k.txt`):

| Evaluation Category | Test Case ID | Target Disclosure | Result | Latency |
| :--- | :--- | :--- | :---: | :---: |
| **Multi-Hop Table Math** | `SEC-001` | YoY Cloud Revenue growth (+24.5%) | **PASSED** | 1066 ms |
| **Footnote Needle-in-Haystack** | `SEC-002` | Antitrust inquiry reserve ($185.0M) | **PASSED** | 1328 ms |
| **Non-GAAP Reconciliation** | `SEC-003` | Adjusted EBITDA & SBC add-back ($1,497.2M) | **PASSED** | 1021 ms |
| **Discontinued Operations** | `SEC-004` | Divestiture of Subsea Fiber ($412.5M) | **PASSED** | 1042 ms |
| **Contradiction Resolution** | `SEC-005` | Press release vs audited GAAP discrepancy | **PASSED** | 1058 ms |
| **Segment Margin Comparison**| `SEC-006` | Cloud vs Cyber-Physical operating margins | **PASSED** | 1245 ms |
| **Balance Sheet Calculation** | `SEC-007` | Net debt computation ($14.2B debt - $6.85B cash) | **PASSED** | 1087 ms |
| **Unanswerable Abstention** | `SEC-008` | Missing FY2019 gross margin (Abstention) | **PASSED** | 1043 ms |
| **Security Injection Block** | `SEC-009` | System prompt extraction attempt (Blocked) | **PASSED** | 1044 ms |
| **False Assertion Refutation** | `SEC-010` | Adversarial claim refutation (NLI Contradiction) | **PASSED** | 1063 ms |

### Aggregate Adversarial Metrics
| Metric | Result | Benchmark Target | Status |
| :--- | :---: | :---: | :---: |
| **Hit@1** | **100.0%** | $\ge 80.0\%$ | Exceeded |
| **Hit@3** | **100.0%** | $\ge 90.0\%$ | Exceeded |
| **Hit@5** | **100.0%** | $\ge 95.0\%$ | Exceeded |
| **NLI Entailment Grounding Rate** | **100.0%** | $\ge 85.0\%$ | Exceeded |
| **Adversarial Abstention Accuracy** | **100.0%** | $\ge 90.0\%$ | Exceeded |
| **P50 Latency** | **1063.3 ms** | $< 1500\text{ ms}$ | Production SLA |
| **P90 Latency** | **1328.6 ms** | $< 2500\text{ ms}$ | Production SLA |

*Note: Telemetry archived in `benchmarks/results/adversarial_sec10k_report.json`.*

---

## 4. Progressive Retrieval Funnel Ablation

Ablation matrix comparing progressive strategies across identical queries:

| Strategy | Hit@1 | Hit@3 | Hit@5 | MRR@5 | NDCG@5 | Claim Faithfulness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Simple Flat Chunking** (Fixed 512, Dense Only) | 58.3% | 61.5% | 61.5% | 0.598 | 0.620 | 68.0% |
| **2. Structure-Aware Chunking** (Dense Only) | 62.5% | 66.7% | 69.2% | 0.645 | 0.710 | 72.5% |
| **3. Hybrid Search** (Dense + BM25 RRF) | 75.0% | 79.2% | 83.3% | 0.771 | 0.845 | 76.0% |
| **4. Document AST + Rerank + NLI Gating** (Tier-1) | **100.0%**| **100.0%**| **100.0%**| **1.000** | **0.985** | **100.0%** |

---

## 5. Reproducing Benchmarks

```bash
# Run Adversarial SEC 10-K Benchmark Suite
python benchmarks/run_adversarial_eval.py

# Run Progressive Strategy Comparison
python benchmarks/compare_strategies.py

# Run Standard 25-Query Regression Evaluation
python benchmarks/run_benchmark.py --samples 25
```
