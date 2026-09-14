# Benchmark Dataset

## Overview

Financial Document Intelligence Benchmark designed to evaluate RAG systems on public financial documents (SEC filings, annual reports, quarterly reports).

## Target Size

- **Minimum**: 200 questions
- **Ideal**: 300+ questions
- **Current**: 20 template questions (needs expansion)

## Question Categories

| Category | Description | Count |
|----------|-------------|-------|
| Direct Lookup | Single fact from one passage | 1 |
| Exact Entity | Named entity lookup | 1 |
| Numerical | Exact numerical extraction | 3 |
| Definition | Define financial term | 0 |
| Comparison | Compare metrics across periods | 1 |
| Summarization | Summarize section/topic | 1 |
| Multi-hop | Combine info from multiple passages | 1 |
| Cross-section | Span sections of one document | 0 |
| Cross-document | Span multiple documents | 0 |
| Temporal | Time-dependent questions | 2 |
| Ambiguous | Multiple interpretations | 0 |
| Unanswerable | Answer not in documents | 1 |
| Contradictory | Conflicting information | 1 |
| Adversarial | Hallucination/injection tests | 2 |
| Long-context | Deep in large document | 0 |
| Table-based | From financial tables | 0 |
| Calculation | Arithmetic on extracted values | 3 |
| Citation-sensitive | Precise attribution needed | 0 |

## Question Structure

Each question includes:

```json
{
  "question_id": "fin-001",
  "question": "What was total revenue for FY2024?",
  "category": "numerical",
  "difficulty": 1,
  "documents": ["10-K_FY2024.pdf"],
  "gold_answer": "Total revenue was $45.2 billion for FY2024.",
  "gold_sources": ["10-K_FY2024.pdf"],
  "gold_pages": [28],
  "answerability": true,
  "expected_citations": 1
}
```

## Document Set

**Target**: Public financial documents from SEC EDGAR

**Types**:
- 10-K annual reports
- 10-Q quarterly reports
- Earnings releases
- Investor presentations

**Companies** (examples):
- Technology company (3 years of filings)
- Healthcare company (3 years of filings)
- Financial services company (3 years of filings)

**Years**: FY2022, FY2023, FY2024

## Construction Methodology

1. **Select documents**: Download real SEC filings
2. **Identify key facts**: Revenue, margins, growth rates, segments
3. **Create questions**: Cover all 18 categories
4. **Verify answers**: Manually check each answer against documents
5. **Assign metadata**: Category, difficulty, sources, pages
6. **Create unanswerable**: Questions with no answer in documents
7. **Create adversarial**: Prompt injection and hallucination tests
8. **Create contradictory**: Same metric reported differently in different docs

## Important Notes

⚠️ **Template questions must be verified against actual documents before use in formal evaluation.**

⚠️ **Gold answers are illustrative — they must be replaced with actual values from real documents.**

⚠️ **Do not use this benchmark for claims about system performance until questions are verified.**

## Expanding the Benchmark

To expand from 20 to 200+ questions:

1. Download 10-15 real SEC filings (3 companies × 3-5 years)
2. For each document, create:
   - 5 numerical questions (revenue, margins, EPS, etc.)
   - 3 temporal questions (year-over-year changes)
   - 2 comparison questions (segments, periods)
   - 2 multi-hop questions (causes, reasons)
   - 1 summarization question
   - 1 unanswerable question
   - 1 adversarial question
3. Verify each answer against the actual document
4. Assign gold_pages by finding the exact page

## Evaluation Metrics

For each question, measure:
- **Retrieval**: Did the system retrieve the correct passage?
- **Generation**: Is the answer factually correct?
- **Citation**: Does the citation point to the right source?
- **Abstention**: Did the system correctly refuse unanswerable questions?

## Status

**TEMPLATE DATASET** — 20 illustrative questions. Needs expansion to 200+ verified questions using real financial documents.
