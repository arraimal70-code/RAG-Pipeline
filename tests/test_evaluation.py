"""
tests/test_evaluation.py — Unit test suite for Phase 6: Automated RAGAS Benchmarking.
"""

from src.evaluation.ragas_runner import RAGASDatasetItem, RAGASRunner


def test_ragas_faithfulness_entailed():
    runner = RAGASRunner()
    contexts = [
        "Consolidated Alphabet revenues reached $350 billion in fiscal 2024, an increase of 15% year-over-year.",
    ]
    answer = "Alphabet reported consolidated revenues of $350 billion in 2024, up 15%."

    faithfulness = runner.compute_faithfulness(answer, contexts)
    assert faithfulness >= 0.8


def test_ragas_faithfulness_unsupported():
    runner = RAGASRunner()
    contexts = [
        "Consolidated Alphabet revenues reached $350 billion in fiscal 2024.",
    ]
    answer = "Alphabet acquired three quantum computing startups in Europe for $50 billion."

    faithfulness = runner.compute_faithfulness(answer, contexts)
    assert faithfulness <= 0.5


def test_ragas_answer_relevancy():
    runner = RAGASRunner()
    question = "What was the operating profit of Google Services?"
    relevant_answer = "Google Services operating profit was $95.5 billion in fiscal year 2024."
    irrelevant_answer = "The boiling point of liquid nitrogen is 77 kelvins under standard pressure."

    rel_score = runner.compute_answer_relevancy(question, relevant_answer)
    irrel_score = runner.compute_answer_relevancy(question, irrelevant_answer)

    assert rel_score > irrel_score
    assert rel_score >= 0.65


def test_ragas_context_precision():
    runner = RAGASRunner()
    question = "Where are the new datacenter clusters located?"
    ground_truth = "New AI datacenter clusters were deployed in Iowa, Nebraska, and Finland."

    top_contexts = [
        "New AI datacenter clusters were deployed in Iowa, Nebraska, and Finland to support TPU v5e.",
        "Consumer hardware distribution centers were expanded in Ohio.",
    ]
    buried_contexts = [
        "Consumer hardware distribution centers were expanded in Ohio.",
        "New AI datacenter clusters were deployed in Iowa, Nebraska, and Finland to support TPU v5e.",
    ]

    top_prec = runner.compute_context_precision(question, top_contexts, ground_truth)
    buried_prec = runner.compute_context_precision(question, buried_contexts, ground_truth)

    assert top_prec >= buried_prec
    assert top_prec > 0.7


def test_ragas_context_recall():
    runner = RAGASRunner()
    ground_truth = "Operating income reached $24.6 billion in fiscal 2023."
    contexts = [
        "Amazon Web Services (AWS) segment operating income grew to $24.6 billion in 2023.",
    ]

    recall = runner.compute_context_recall(ground_truth, contexts)
    assert recall >= 0.8


def test_ragas_full_dataset_evaluation():
    runner = RAGASRunner()
    items = [
        RAGASDatasetItem(
            question="What is the gross margin for Microsoft Cloud?",
            contexts=["Microsoft Cloud gross margin percentage reached 72% in FY2024."],
            ground_truth="Microsoft Cloud gross margin was 72% in FY2024.",
            answer="In FY2024, Microsoft Cloud reported a 72% gross margin.",
        ),
        RAGASDatasetItem(
            question="What was Apple Services revenue in Q3 2024?",
            contexts=["Apple Services revenue reached $24.2 billion in Q3 2024."],
            ground_truth="Services revenue reached $24.2 billion in Q3 2024.",
            answer="Apple Services revenue was $24.2 billion in Q3 2024.",
        ),
    ]

    result = runner.evaluate_dataset(items)

    assert result.total_samples == 2
    assert result.mean_faithfulness >= 0.8
    assert result.mean_answer_relevancy >= 0.7
    assert result.overall_score >= 0.75
    assert result.p99_latency_ms >= 0.0
