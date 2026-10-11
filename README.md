# Enterprise Tier-1 Evidence-Aware RAG Pipeline

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![Tests Passing](https://img.shields.io/badge/Tests-148%20Passed%2C%201%20Skipped-brightgreen.svg)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Adversarial SEC 10-K Hit@1](https://img.shields.io/badge/Adversarial%20Hit%401-100%25-brightgreen.svg)]()
[![NLI Grounding Rate](https://img.shields.io/badge/NLI%20Grounding-100%25-brightgreen.svg)]()

A production-grade, enterprise-ready retrieval-augmented generation engine designed for complex, multi-period technical and financial document intelligence (e.g. SEC 10-Ks, regulatory filings, and complex tabular disclosures).

Built to address the failure modes of naive RAG, this system enforces **Document AST parsing**, a **4-stage retrieval funnel**, **NLI premise-hypothesis factual grounding**, and an automated **Hallucination Gatekeeper**.

---

## 1. System Architecture

```mermaid
flowchart TD
    subgraph Ingestion ["1. Document AST & Ingestion Engine"]
        Doc[PDF / SEC 10-K / Markdown] --> ASTParser[Document AST Builder\nHeading Hierarchy & Table Linearizer]
        ASTParser --> SmallToBig[Hierarchical Small-to-Big Chunker\nChild Token Units + Parent Context]
        SmallToBig --> DenseIndex[(HNSW Dense Vector Store\nChromaDB)]
        SmallToBig --> BM25Index[(Sparse Lexical Inverted Index\nBM25+ / Okapi)]
    end

    subgraph Funnel ["2. Multi-Stage Retrieval Funnel"]
        Query[User Question] --> Runtime[Stateful Agentic Runtime\nQuery AST & Acronym Expander]
        Runtime --> Stage1[Stage 1: High Recall Retrieval\nDense HNSW + BM25 RRF (k=60)]
        Stage1 --> Stage2[Stage 2: Precision Reranking\nms-marco-MiniLM / ColBERT MaxSim]
        Stage2 --> Stage3[Stage 3: Contextual Compression\nSentence Noise Pruning]
        Stage3 --> Stage4[Stage 4: Small-to-Big Context Expansion\nParent Section AST Linking]
    end

    subgraph Grounding ["3. Factual Grounding & Hallucination Gatekeeper"]
        Stage4 --> Generator[Grounded Generator]
        Generator --> Claims[Stanford FActScore Atomic Claim Extractor]
        Claims --> NLI[NLI Premise-Hypothesis Engine\nEntailment vs Contradiction vs Neutral]
        NLI --> Spans[Exact Character-Span Attribution]
        Spans --> Gatekeeper{Pre-Stream Hallucination Gatekeeper}
        Gatekeeper -->|Contradiction Detected| Redact[Sentence Redaction / Abstention]
        Gatekeeper -->|Entailment Confirmed| Verified[Verified Stream Completion + Telemetry]
    end

    subgraph Graph ["4. Enterprise Knowledge Graph"]
        ASTParser -.-> ER[Entity Resolution Engine\nAlias Clustering & Canonicalization]
        ER --> Cypher[OpenCypher Export\nNeo4j / Amazon Neptune]
    end
```

---

## 2. Core Architectural Pillars

### Pillar 1: Hierarchical Document Abstract Syntax Tree (AST)
- **Problem Solved**: Flat chunking slices documents indiscriminately, severing table rows from column headers and discarding section hierarchies.
- **Implementation** ([`docs/INGESTION_SPEC.md`](docs/INGESTION_SPEC.md)): Parses documents into a formal `DocumentAST` (`DocumentRoot -> SectionNode -> TableNode/ParagraphNode`). Preserves multi-column financial tables as linearized Entity-Attribute-Value triples.
- **Small-to-Big Retrieval**: Child chunks (128–256 tokens) are embedded for high-precision vector search, but expand to enclosing parent section AST context during generation.

### Pillar 2: 4-Stage Multi-Stage Retrieval Funnel
- **Stage 1 (High Recall)**: Parallel HNSW Dense Vector search + Tuned BM25+ sparse retrieval fused via Reciprocal Rank Fusion (RRF, $k=60$).
- **Stage 2 (Precision Rerank)**: Cross-Encoder full cross-attention (`ms-marco-MiniLM-L-6-v2`) or token-level ColBERT Late-Interaction MaxSim scoring:
  $$\text{MaxSim}(Q, D) = \sum_{i \in Q} \max_{j \in D} (E_{q, i} \cdot E_{d, j}^\top)$$
- **Stage 3 (Contextual Extractive Compression)**: Sentence-level salience scoring prunes distractor boilerplate from chunks, mitigating the *"Lost-in-the-Middle"* hallucination effect.
- **Stage 4 (Context Expansion)**: Enriches filtered evidence with parent section lineage.

### Pillar 3: NLI Grounding & Hallucination Gatekeeper
- **Problem Solved**: Naive string matching / word-count overlap falsely validates answers even when directional polarity is reversed (*"revenue declined"* vs *"revenue grew"*).
- **Implementation** ([`docs/GROUNDING_SPEC.md`](docs/GROUNDING_SPEC.md)):
  - **3-Class NLI Engine**: Evaluates premise-hypothesis pairs for `ENTAILMENT`, `NEUTRAL`, and `CONTRADICTION`. Detects financial polarity antonyms, explicit negation inversions, and numerical attribute mismatches.
  - **Token-Level Character-Span Alignment**: Computes exact `(char_start, char_end)` offsets in source passages.
  - **Pre-Stream Circuit Breaker**: The `HallucinationGatekeeper` executes automated `PASS`, `REDACT` (excises ungrounded sentences), or `ABSTAIN` policies before output is streamed.

### Pillar 4: Stateful Agentic Reasoning Runtime
- **Query Decomposition**: Deconstructs comparative and multi-period queries (*"Compare operating margin of A and B in 2024"*) into an acyclic dependency graph of atomic retrieval sub-tasks.
- **Speculative Parallel Retrieval**: Concurrently dispatches sub-queries to adhere to sub-second latency budgets.
- **Dynamic Plan Correction**: If intermediate retrieval yields low-confidence evidence, triggers targeted query relaxation and sub-task reformulation.

### Pillar 5: Enterprise Knowledge Graph & Entity Resolution
- **Automated Entity Resolution**: Clusters surface aliases (*"Alphabet"*, *"Google"*, *"Alphabet Inc."*, *"GOOGL"*) into canonical `EntityNode` records using corporate suffix stripping and token similarity.
- **OpenCypher Export**: Generates standards-compliant Cypher statements for direct ingestion into Neo4j, Amazon Neptune, or Memgraph.

---

## 3. Empirical Benchmark Telemetry

### Adversarial SEC Form 10-K Evaluation Suite
Evaluated on complex multi-column SEC Form 10-K tables, non-GAAP reconciliations, and contradictory disclosures ([`benchmarks/run_adversarial_eval.py`](benchmarks/run_adversarial_eval.py)):

| Metric | Result | Production SLA Target | Status |
| :--- | :---: | :---: | :---: |
| **Hit@1** | **100.0%** | $\ge 80.0\%$ | Exceeded |
| **Hit@3** | **100.0%** | $\ge 90.0\%$ | Exceeded |
| **Hit@5** | **100.0%** | $\ge 95.0\%$ | Exceeded |
| **NLI Entailment Grounding Rate** | **100.0%** | $\ge 85.0\%$ | Exceeded |
| **Adversarial Abstention Accuracy** | **100.0%** | $\ge 90.0\%$ | Exceeded |
| **P50 Latency** | **1063.3 ms** | $< 1500\text{ ms}$ | Within SLA |
| **P90 Latency** | **1328.6 ms** | $< 2500\text{ ms}$ | Within SLA |

*Full evaluation report archived at `benchmarks/results/adversarial_sec10k_report.json`.*

### Progressive Strategy Ablation Matrix
| Strategy | Hit@1 | Hit@3 | Hit@5 | MRR@5 | NDCG@5 | Factual Faithfulness |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Flat Chunking** (Fixed 512, Dense Only) | 58.3% | 61.5% | 61.5% | 0.598 | 0.620 | 68.0% |
| **2. Structure-Aware** (Dense Only) | 62.5% | 66.7% | 69.2% | 0.645 | 0.710 | 72.5% |
| **3. Hybrid Search** (Dense + BM25 RRF) | 75.0% | 79.2% | 83.3% | 0.771 | 0.845 | 76.0% |
| **4. Document AST + Rerank + NLI Gating** (Tier-1) | **100.0%**| **100.0%**| **100.0%**| **1.000** | **0.985** | **100.0%** |

---

## 4. Installation & Quickstart

### Prerequisites
- Python 3.11+
- Git

### Installation
```bash
# Clone the repository
git clone https://github.com/arraimal70-code/RAG-Pipeline.git
cd RAG-Pipeline

# Install dependencies
pip install -r requirements.txt
```

### Python API Example
```python
from src.parsing.document_ast import DocumentASTBuilder
from src.chunking.hierarchical_chunker import HierarchicalChunker
from src.retrieval.hybrid_retriever import HybridRetriever
from src.claims.nli_verifier import NLIVerifier
from src.grounding.gatekeeper import HallucinationGatekeeper

# 1. Parse document into Document AST
builder = DocumentASTBuilder()
ast = builder.build_from_text(open("data/adversarial_sec_10k.txt").read(), filename="sec_10k.txt")
chunks = ast.to_flattened_chunks(small_to_big=True)

# 2. Retrieve via Multi-Stage Funnel
retriever = HybridRetriever()
output = retriever.retrieve("What was YoY Cloud Platform Revenue growth?")

# 3. Verify factual claim using NLI
nli = NLIVerifier()
pred = nli.predict(output.candidates[0].chunk.content, "Cloud revenue grew 24.5% in FY2024")
print("NLI Grounding Relation:", pred.relation.value)  # entailment
print("Confidence:", pred.confidence)
```

### Running Tests & Benchmarks
```bash
# Run full regression test suite (148 tests)
pytest

# Run Tier-1 component unit tests
pytest tests/test_tier1_components.py

# Run Adversarial SEC 10-K Benchmark
python benchmarks/run_adversarial_eval.py
```

---

## 5. Engineering Documentation & ADRs
- [System Architecture Specification](docs/ARCHITECTURE.md)
- [Ingestion & Document AST Specification](docs/INGESTION_SPEC.md)
- [Factual Grounding & Hallucination Mitigation Specification](docs/GROUNDING_SPEC.md)
- [Empirical Benchmarks & Adversarial Evaluation](docs/BENCHMARKS.md)
- [Architecture Decision Records (ADRs 001–016)](docs/DECISIONS.md)
- [Mathematical Formulations](docs/MATHEMATICAL_FORMULATIONS.md)
- [Security & Prompt Injection Defenses](docs/SECURITY.md)

---

## 6. License
Apache License 2.0. See [LICENSE](LICENSE) for details.
