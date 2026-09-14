#!/usr/bin/env python3
"""
Execute RAG pipeline experiments and save raw results.

This script runs the actual experiments defined in the experiment manifest
and saves raw results (not pre-computed metrics) for later analysis.
"""

import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.core.config import config
from src.pipeline import RAGPipeline
from src.evaluation.evaluator import Evaluator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentExecutor:
    """Execute experiments and save raw results."""
    
    def __init__(self, output_dir: str = "experiments/results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.pipeline = RAGPipeline()
        self.evaluator = Evaluator()
        
    def load_benchmark(self, benchmark_path: str = "benchmarks/comprehensive_benchmark_200.json") -> List[Dict]:
        """Load benchmark questions."""
        with open(benchmark_path, "r") as f:
            data = json.load(f)
        return data["questions"]
    
    def run_single_query(self, question: str) -> Dict[str, Any]:
        """Run a single query and return raw results."""
        start_time = time.time()
        
        try:
            # Run pipeline
            response = self.pipeline.query(question)
            
            # Extract raw data
            raw_result = {
                "query": question,
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": (time.time() - start_time) * 1000,
                "success": True,
                "response": {
                    "answer": response.answer,
                    "confidence": response.confidence,
                    "support_level": response.support_level.value if hasattr(response.support_level, 'value') else str(response.support_level),
                    "abstained": response.abstained,
                    "citations": [
                        {
                            "source": getattr(c, 'source', None) or getattr(c, 'document', None),
                            "page": getattr(c, 'page', None),
                            "excerpt": getattr(c, 'excerpt', None) or getattr(c, 'relevant_text', None),
                        }
                        for c in response.citations
                    ],
                },
                "retrieval_metadata": response.retrieval_metadata if hasattr(response, 'retrieval_metadata') else {},
            }
            
            return raw_result
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return {
                "query": question,
                "timestamp": datetime.utcnow().isoformat(),
                "latency_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error": str(e),
            }
    
    def run_experiment(
        self,
        experiment_id: str,
        questions: List[Dict],
        config_override: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Run an experiment on a set of questions."""
        logger.info(f"Running experiment {experiment_id} on {len(questions)} questions")
        
        start_time = time.time()
        results = []
        
        for i, question_data in enumerate(questions, 1):
            question = question_data["question"]
            logger.info(f"  [{i}/{len(questions)}] {question[:50]}...")
            
            result = self.run_single_query(question)
            result["question_id"] = question_data.get("question_id", f"Q{i:03d}")
            result["expected_answer"] = question_data.get("expected_answer", "")
            result["source_document"] = question_data.get("source_document", "")
            result["query_type"] = question_data.get("query_type", "")
            result["difficulty"] = question_data.get("difficulty", "")
            
            results.append(result)
        
        total_time = time.time() - start_time
        
        experiment_result = {
            "experiment_id": experiment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "config": config_override or {},
            "total_questions": len(questions),
            "successful_queries": sum(1 for r in results if r["success"]),
            "failed_queries": sum(1 for r in results if not r["success"]),
            "total_time_seconds": total_time,
            "avg_latency_ms": sum(r["latency_ms"] for r in results if r["success"]) / max(1, sum(1 for r in results if r["success"])),
            "results": results,
        }
        
        return experiment_result
    
    def save_results(self, experiment_result: Dict[str, Any]) -> Path:
        """Save experiment results to file."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{experiment_result['experiment_id']}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(experiment_result, f, indent=2)
        
        logger.info(f"Results saved to {filepath}")
        return filepath
    
    def run_all_experiments(self, benchmark_path: str = "benchmarks/comprehensive_benchmark_200.json"):
        """Run all defined experiments."""
        questions = self.load_benchmark(benchmark_path)
        logger.info(f"Loaded {len(questions)} benchmark questions")
        
        # Define experiments
        experiments = [
            {
                "id": "EXP-01_dense_baseline",
                "description": "Dense retrieval only",
                "config": {
                    "retrieval": {
                        "dense_top_k": 50,
                        "bm25_top_k": 0,
                        "rerank_enabled": False,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-02_bm25_baseline",
                "description": "BM25 retrieval only",
                "config": {
                    "retrieval": {
                        "dense_top_k": 0,
                        "bm25_top_k": 50,
                        "rerank_enabled": False,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-03_hybrid_rrf",
                "description": "Hybrid retrieval with RRF fusion",
                "config": {
                    "retrieval": {
                        "dense_top_k": 50,
                        "bm25_top_k": 50,
                        "fusion_method": "rrf",
                        "rerank_enabled": False,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-04_hybrid_dense_heavy",
                "description": "Hybrid with dense-heavy weighting",
                "config": {
                    "retrieval": {
                        "dense_weight": 0.8,
                        "bm25_weight": 0.2,
                        "fusion_method": "weighted",
                        "rerank_enabled": False,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-05_hybrid_lexical_heavy",
                "description": "Hybrid with lexical-heavy weighting",
                "config": {
                    "retrieval": {
                        "dense_weight": 0.2,
                        "bm25_weight": 0.8,
                        "fusion_method": "weighted",
                        "rerank_enabled": False,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-06_adaptive_retrieval",
                "description": "Adaptive retrieval with query classification",
                "config": {
                    "retrieval": {
                        "adaptive_enabled": True,
                        "rerank_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-07_hybrid_rerank",
                "description": "Hybrid retrieval with reranking",
                "config": {
                    "retrieval": {
                        "dense_top_k": 50,
                        "bm25_top_k": 50,
                        "fusion_method": "rrf",
                        "rerank_enabled": True,
                        "adaptive_enabled": False,
                    }
                }
            },
            {
                "id": "EXP-08_adaptive_rerank",
                "description": "Adaptive retrieval with reranking (full system)",
                "config": {
                    "retrieval": {
                        "adaptive_enabled": True,
                        "rerank_enabled": True,
                    }
                }
            },
        ]
        
        # Run experiments
        for exp in experiments:
            logger.info(f"\n{'='*80}")
            logger.info(f"Running: {exp['id']}")
            logger.info(f"Description: {exp['description']}")
            logger.info(f"{'='*80}")
            
            result = self.run_experiment(exp["id"], questions, exp["config"])
            filepath = self.save_results(result)
            
            logger.info(f"✓ Completed: {result['successful_queries']}/{result['total_questions']} successful")
            logger.info(f"✓ Avg latency: {result['avg_latency_ms']:.2f}ms")
            logger.info(f"✓ Results saved to: {filepath}")


def main():
    """Main entry point."""
    executor = ExperimentExecutor()
    executor.run_all_experiments()


if __name__ == "__main__":
    main()
