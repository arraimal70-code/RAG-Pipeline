#!/usr/bin/env python3
"""
scripts/validate_benchmark.py — Benchmark validation tool.

Validates benchmark dataset quality and integrity.
Returns non-zero exit status if benchmark is invalid.
"""

import json
import sys
from pathlib import Path
from typing import Any
from collections import Counter


class BenchmarkValidator:
    """Validates benchmark dataset quality."""

    REQUIRED_FIELDS = [
        "question_id",
        "question",
        "category",
        "difficulty",
        "answerable",
    ]

    ANSWERABLE_FIELDS = [
        "expected_answer",
        "gold_sources",
    ]

    UNANSWERABLE_FIELDS = [
        "expected_behavior",
    ]

    VALID_CATEGORIES = [
        "direct_lookup",
        "semantic_conceptual",
        "numerical",
        "definition",
        "comparison",
        "summarization",
        "multi_hop",
        "cross_section",
        "cross_document",
        "ambiguous",
        "unanswerable",
        "adversarial",
        "table_based",
        "contradictory",
        "temporal",
        "long_context",
        "citation_verification",
        "evidence_insufficiency",
        "entity_matching",
        "calculation",
    ]

    def __init__(self, benchmark_path: Path):
        self.benchmark_path = benchmark_path
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.stats: dict[str, Any] = {}

    def validate(self) -> bool:
        """Run all validation checks."""
        print(f"Validating benchmark: {self.benchmark_path}")
        print("=" * 60)

        # Load benchmark
        try:
            with open(self.benchmark_path) as f:
                data = json.load(f)
        except Exception as e:
            self.errors.append(f"Failed to load benchmark: {e}")
            return False

        # Extract questions
        questions = data.get("questions", [])
        if not questions:
            self.errors.append("No questions found in benchmark")
            return False

        print(f"Found {len(questions)} questions")

        # Validate each question
        for i, q in enumerate(questions):
            self._validate_question(q, i)

        # Validate dataset-level properties
        self._validate_dataset(questions)

        # Print results
        self._print_results()

        return len(self.errors) == 0

    def _validate_question(self, q: dict, index: int) -> None:
        """Validate a single question."""
        qid = q.get("question_id", f"question_{index}")

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in q:
                self.errors.append(f"{qid}: Missing required field '{field}'")

        # Check for placeholder content
        question_text = q.get("question", "")
        if "[VERIFY]" in question_text or "TODO" in question_text:
            self.errors.append(f"{qid}: Contains placeholder text")

        if "sample_document" in str(q).lower():
            self.errors.append(f"{qid}: References placeholder document")

        # Validate category
        category = q.get("category")
        if category and category not in self.VALID_CATEGORIES:
            self.errors.append(f"{qid}: Invalid category '{category}'")

        # Validate difficulty
        difficulty = q.get("difficulty")
        if difficulty is not None:
            if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 5:
                self.errors.append(f"{qid}: Invalid difficulty (must be 1-5)")

        # Validate answerable-specific fields
        answerable = q.get("answerable", True)
        if answerable:
            for field in self.ANSWERABLE_FIELDS:
                if field not in q:
                    self.errors.append(f"{qid}: Answerable question missing '{field}'")

            # Check for placeholder answers
            expected = q.get("expected_answer", "")
            if "[VERIFY]" in expected or "TODO" in expected:
                self.errors.append(f"{qid}: Expected answer contains placeholder")

            if not expected or expected.strip() == "":
                self.errors.append(f"{qid}: Empty expected answer")

        # Validate unanswerable-specific fields
        if not answerable:
            if "expected_behavior" not in q:
                self.warnings.append(f"{qid}: Unanswerable question should have 'expected_behavior'")

        # Check for duplicate question IDs
        # (handled in dataset validation)

        # Check question length
        if len(question_text) < 10:
            self.warnings.append(f"{qid}: Question seems too short")

        if len(question_text) > 500:
            self.warnings.append(f"{qid}: Question seems too long")

    def _validate_dataset(self, questions: list[dict]) -> None:
        """Validate dataset-level properties."""
        # Check for duplicate IDs
        ids = [q.get("question_id") for q in questions]
        duplicates = [id for id, count in Counter(ids).items() if count > 1]
        if duplicates:
            self.errors.append(f"Duplicate question IDs: {duplicates}")

        # Check category distribution
        categories = [q.get("category") for q in questions if q.get("category")]
        category_counts = Counter(categories)

        self.stats["total_questions"] = len(questions)
        self.stats["answerable"] = sum(1 for q in questions if q.get("answerable", True))
        self.stats["unanswerable"] = sum(1 for q in questions if not q.get("answerable", True))
        self.stats["category_distribution"] = dict(category_counts)

        # Check for category imbalance
        if len(questions) >= 50:
            min_count = min(category_counts.values()) if category_counts else 0
            if min_count < 3:
                self.warnings.append(f"Category imbalance: some categories have < 3 questions")

        # Check for minimum size
        if len(questions) < 100:
            self.warnings.append(f"Benchmark has only {len(questions)} questions (recommended: 150+)")

        # Check difficulty distribution
        difficulties = [q.get("difficulty", 3) for q in questions]
        diff_counts = Counter(difficulties)
        self.stats["difficulty_distribution"] = dict(diff_counts)

    def _print_results(self) -> None:
        """Print validation results."""
        print("\nValidation Results:")
        print("-" * 60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")

        print(f"\n📊 STATISTICS:")
        print(f"  Total questions: {self.stats.get('total_questions', 0)}")
        print(f"  Answerable: {self.stats.get('answerable', 0)}")
        print(f"  Unanswerable: {self.stats.get('unanswerable', 0)}")

        if "category_distribution" in self.stats:
            print(f"\n  Category distribution:")
            for cat, count in sorted(self.stats["category_distribution"].items()):
                print(f"    {cat}: {count}")

        if "difficulty_distribution" in self.stats:
            print(f"\n  Difficulty distribution:")
            for diff, count in sorted(self.stats["difficulty_distribution"].items()):
                print(f"    Level {diff}: {count}")

        print("\n" + "=" * 60)
        if self.errors:
            print(f"❌ VALIDATION FAILED: {len(self.errors)} errors")
        elif self.warnings:
            print(f"⚠️  VALIDATION PASSED WITH WARNINGS: {len(self.warnings)} warnings")
        else:
            print("✅ VALIDATION PASSED")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate_benchmark.py <benchmark.json>")
        sys.exit(1)

    benchmark_path = Path(sys.argv[1])
    if not benchmark_path.exists():
        print(f"Error: File not found: {benchmark_path}")
        sys.exit(1)

    validator = BenchmarkValidator(benchmark_path)
    is_valid = validator.validate()

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
