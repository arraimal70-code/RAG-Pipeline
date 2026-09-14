# RAG Pipeline — Evidence-Aware Adaptive Document Intelligence

> **Status**: Infrastructure complete. **Experiments pending execution.**
> 
> **Current Score**: 2.4/10 (per FINAL_TECHNICAL_AUDIT.md)

A research-grade Retrieval-Augmented Generation (RAG) system that investigates how to dynamically balance retrieval quality, factual reliability, citation correctness, latency, and computational cost while recognizing when available evidence is insufficient.

---

## ⚠️ Honest Status

**What exists:**
- ✅ Complete code infrastructure for adaptive, evidence-aware RAG
- ✅ 19 experiments + ablation studies defined
- ✅ Comprehensive evaluation framework
- ✅ 20-category benchmark structure
- ✅ Security validation framework
- ✅ Performance measurement tools

**What does NOT exist:**
- ❌ **No experiments have been executed**
- ❌ **No real results have been generated**
- ❌ **No performance has been measured**
- ❌ **No real-world validation has occurred**
- ❌ **No statistical analysis has been performed**

**To get real results, you must:**
1. Obtain actual financial documents (SEC filings)
2. Set up OpenAI API key
3. Run `python experiments/runner.py`
4. Run `python scripts/measure_performance.py`
5. Run `python scripts/validate_realworld.py`

**Any numbers claiming performance metrics are placeholders until experiments are actually run.**

---

## 🏗️ Architecture

```
Query → Query Analysis → Adaptive Retrieval → Reranking
  ↓
Evidence Sufficiency → Decision (Answer/Abstain/Retrieve More)
  ↓
LLM Generation → Citation Validation → Claim Analysis
  ↓
Response with Citations + Confidence + Tracing
```

### Core Components

| Component | Status | Description |
|-----------|--------|-------------|
| **Adaptive Retrieval** | ✅ Implemented | Query-type-aware weight adjustment |
| **Hybrid Retrieval** | ✅ Implemented | Dense + BM25 + RRF fusion |
| **Cross-Encoder Reranking** | ✅ Implemented | Precision improvement |
| **Evidence Sufficiency** | ✅ Implemented | Multi-signal assessment |
| **Numerical Reasoning** | ✅ Implemented | Programmatic calculation |
| **Temporal Reasoning** | ✅ Implemented | Period-aware retrieval |
| **Citation Validation** | ✅ Implemented | Structural validation |
| **Claim Analysis** | ✅ Implemented | Atomic claim evaluation |
| **Contradiction Detection** | ✅ Implemented | Conflict identification |
| **Observability** | ✅ Implemented | Full query tracing |

---

## 📊 Benchmark

**Current Status**: Template structure with 10 example questions

**Target**: 150-300 verified questions across 20 categories

**Categories**:
1. Direct lookup
2. Semantic/conceptual
3. Numerical
4. Definition
5. Comparison
6. Summarization
7. Multi-hop
8. Cross-section
9. Cross-document
10. Ambiguous
11. Unanswerable
12. Adversarial
13. Table-based
14. Contradictory
15. Temporal
16. Long-context
17. Citation verification
18. Evidence insufficiency
19. Entity matching
20. Calculation

**Validation**: Run `python scripts/validate_benchmark.py benchmarks/benchmark_v2.json`

---

## 🧪 Experiments

**19 experiments + 6 ablation studies defined:**

### Retrieval Strategy
- EXP-01: Dense baseline
- EXP-02: BM25 baseline
- EXP-03: Hybrid RRF
- EXP-04: Dense-heavy hybrid
- EXP-05: Lexical-heavy hybrid
- EXP-06: Adaptive hybrid

### Chunking
- EXP-07: Fixed vs Sentence vs Recursive vs Structure-aware

### Components
- EXP-09: Reranking impact
- EXP-10: Top-K sensitivity
- EXP-11: Evidence sufficiency
- EXP-12: Citation validation
- EXP-13: Contradiction detection

### Ablations
- EXP-ABL-1 to EXP-ABL-5: Remove individual components

### Full System
- EXP-19: Full optimized pipeline

**Status**: ❌ **Not yet executed** — Run with `python experiments/runner.py`

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/arraimal70-code/RAG-Pipeline.git
cd RAG-Pipeline
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your OPENAI_API_KEY
```

### 2. Prepare Documents

```bash
mkdir -p data/documents
# Add your PDF documents (e.g., SEC filings)
```

### 3. Ingest

```bash
python -m src.pipeline ingest data/documents/
```

### 4. Query

```bash
python -m src.pipeline query "What was the revenue in 2023?"
```

### 5. Run Experiments

```bash
python experiments/runner.py
```

### 6. Measure Performance

```bash
python scripts/measure_performance.py
```

---

## 📈 Results

**Status**: ❌ **NOT YET MEASURED**

To generate results:
1. Obtain real financial documents (SEC filings)
2. Populate benchmark with 150-300 verified questions
3. Run all experiments
4. Analyze results

**Expected Metrics**:
- Retrieval: Recall@K, MRR, nDCG
- Generation: Factual correctness, groundedness
- Citations: Precision, recall, validation accuracy
- System: Latency (p50, p95), token usage, cost
- Abstention: Correct refusal rate, false refusal rate

---

## 🔬 Key Innovations

### 1. Evidence-Aware Adaptive Retrieval

Instead of fixed retrieval weights, the system:
- Classifies query type (numerical, conceptual, comparison, etc.)
- Adjusts dense/BM25 weights based on query characteristics
- Expands retrieval for ambiguous queries
- Logs all decisions for analysis

**Research Question**: Does adaptive routing improve retrieval quality?

**Status**: ✅ Implemented, ❌ Not validated experimentally

### 2. Evidence Sufficiency Assessment

Before generating answers, the system assesses:
- Retrieval score quality
- Evidence agreement between sources
- Evidence coverage of the question
- Contradiction presence

Then decides: **Answer** | **Retrieve More** | **Abstain**

**Research Question**: Can evidence checking reduce hallucination?

**Status**: ✅ Implemented, ❌ Not validated experimentally

### 3. Numerical Reasoning

Extracts numerical values and performs programmatic calculations to avoid LLM arithmetic hallucination.

**Example**: "What was the growth rate?" → Extract numbers → Calculate programmatically

**Status**: ✅ Implemented, ❌ Not validated experimentally

### 4. Temporal Reasoning

Ensures retrieved evidence matches the question's time period. Prevents returning FY2023 data for FY2024 questions.

**Status**: ✅ Implemented, ❌ Not validated experimentally

### 5. Claim-Level Faithfulness

Splits answers into atomic claims and evaluates each against evidence independently.

**Example**: "Revenue increased 12%, driven by international sales" → 2 claims → Evaluate each

**Status**: ✅ Implemented, ❌ Not validated experimentally

---

## 🔒 Security

**Implemented Protections**:
- ✅ Input validation (file type, size)
- ✅ Prompt injection pattern detection
- ✅ Resource limits
- ✅ Non-root Docker execution
- ✅ Secrets in environment variables

**Test Coverage**:
- ✅ Basic security tests
- ❌ Comprehensive adversarial testing
- ❌ Penetration testing

**Documentation**: See `docs/SECURITY.md`

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| `docs/ARCHITECTURE.md` | System architecture |
| `docs/RESEARCH_QUESTION.md` | Research questions & hypotheses |
| `docs/METHODOLOGY.md` | Experimental methodology |
| `docs/EXPERIMENTS.md` | Experiment descriptions |
| `docs/BENCHMARK.md` | Benchmark construction |
| `docs/RESULTS.md` | Results (after running) |
| `docs/FINDINGS.md` | Findings (after analysis) |
| `docs/FAILURE_ANALYSIS.md` | Failure taxonomy |
| `docs/SECURITY.md` | Security considerations |
| `docs/LIMITATIONS.md` | Known limitations |
| `docs/DECISIONS.md` | Engineering decisions |
| `docs/REPRODUCIBILITY.md` | Reproduction guide |
| `docs/FINAL_PROJECT_AUDIT.md` | Complete project audit |

---

## ⚠️ Limitations

### Critical

1. **No experimental results** — All claims unvalidated
2. **Benchmark is template** — Needs 150-300 verified questions
3. **Evaluation is heuristic** — Uses support-level as proxy
4. **Single embedding model** — Only MiniLM tested
5. **Single LLM** — Only GPT-4o-mini tested

### Technical

6. **PDF-only** — No other document formats
7. **No OCR** — Scanned documents not handled
8. **No table extraction** — Tables not specially handled
9. **No statistical analysis** — Confidence intervals not computed
10. **No human evaluation** — All metrics automated

### What Should NOT Be Claimed

❌ "The system achieves X% accuracy" (no experiments run)
❌ "Adaptive retrieval outperforms fixed hybrid" (not tested)
❌ "State-of-the-art performance" (no baselines compared)
❌ "Production-ready" (no stress testing)

### What CAN Be Claimed

✅ "The infrastructure for evaluation is complete"
✅ "The system implements adaptive retrieval, evidence sufficiency, and abstention"
✅ "The architecture supports reproducible experiments"
✅ "The code is modular and testable"
✅ "The system treats documents as untrusted input"

---

## 🔄 Reproducibility

### Reproduce Experiments

```bash
# See exact commands
python scripts/reproduce.py

# Run all experiments
python experiments/runner.py

# View results
cat experiments/results/COMPARISON.md
```

### Docker

```bash
docker build -t rag-pipeline .
docker run -p 8000:8000 --env-file .env rag-pipeline
```

### Configuration Snapshot

Every experiment records:
- Full configuration
- Dataset version
- Model versions
- Timestamp
- Git commit SHA

---

## 🎓 Real-World Use Case

**Domain**: Financial Document Intelligence

**Target Users**:
- Financial analysts researching company filings
- Students learning financial analysis
- Investors comparing quarterly reports
- Researchers studying financial trends

**Example Workflow**:
1. Upload 10-K filings for 3 companies (2022-2024)
2. Ask: "How did operating margin change from 2023 to 2024?"
3. System retrieves relevant passages
4. System extracts numerical values
5. System calculates growth rate
6. System provides answer with citations
7. System shows confidence level

**Status**: ❌ **Not yet validated** — Requires real documents

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run integration tests
pytest tests/test_integration.py -v

# Run security tests
pytest tests/test_security.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Coverage**: ~40% (target: 60%+)

---

## 📊 Current Project Score

| Dimension | Score | Justification |
|-----------|-------|---------------|
| Architecture | 8/10 | Clean, modular, well-designed |
| Implementation | 7/10 | Most components implemented, some not integrated |
| Testing | 4/10 | Integration tests added, coverage ~40% |
| Benchmark | 2/10 | Structure exists, needs real questions |
| Experiments | 1/10 | Defined but not executed |
| Results | 0/10 | No results exist |
| Findings | 0/10 | No findings exist |
| Documentation | 8/10 | Comprehensive, honest |
| Security | 5/10 | Basic protections, incomplete testing |
| Performance | 0/10 | Not measured |
| Real-World Validation | 1/10 | Not validated |
| Reproducibility | 6/10 | Can install, cannot reproduce results |

**OVERALL SCORE: 3.5/10**

**Why**: Strong infrastructure, but no evidence. Like a laboratory with all equipment but no experiments run.

---

## 🚀 Next Steps

### Immediate (Research Integrity)

1. **Create real benchmark**
   - Obtain SEC filings
   - Create 150-300 verified questions
   - Validate with `scripts/validate_benchmark.py`

2. **Execute experiments**
   - Run all 19 experiments
   - Generate results
   - Populate RESULTS.md

3. **Analyze findings**
   - Compare retrieval strategies
   - Validate adaptive retrieval
   - Document discoveries

### Secondary (Quality)

4. **Increase test coverage** to 60%+
5. **Measure performance** (latency, cost)
6. **Validate real-world use** with actual documents

### Tertiary (Polish)

7. **Enhance security** (auth, rate limiting)
8. **Test scalability** (10, 100, 1000 documents)
9. **Add human evaluation**

---

## 📄 License

MIT License — See LICENSE file

---

## 🙏 Acknowledgments

Built with:
- LangChain — LLM orchestration
- ChromaDB — Vector storage
- sentence-transformers — Local embeddings
- OpenAI — LLM generation
- FastAPI — API server

---

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Consult the documentation
- Run `python scripts/reproduce.py` for reproduction help

---

**Final Note**: This repository contains excellent infrastructure but requires experimental validation. The architecture is sound, the code is clean, but the central research questions remain unanswered. Run the experiments, generate the evidence, and discover what actually works.
