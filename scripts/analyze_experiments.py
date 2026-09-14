#!/usr/bin/env python3
"""
Analyze raw experiment results and compute metrics.

This script reads raw experiment results and computes:
- Retrieval metrics (Recall@K, Precision@K, MRR, NDCG)
- Generation metrics (answer correctness, citation accuracy)
- Performance metrics (latency, throughput)
- Statistical analysis (confidence intervals, significance tests)
"""

import json
import math
import statistics
from pathlib import Path
from typing import Dict, List, Any, Tuple
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExperimentAnalyzer:
    """Analyze experiment results and compute metrics."""
    
    def __init__(self, results_dir: str = "experiments/results"):
        self.results_dir = Path(results_dir)
        self.analysis_dir = Path("experiments/analysis")
        self.analysis_dir.mkdir(parents=True, exist_ok=True)
        
    def load_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Load experiment results from file."""
        # Find the most recent result file for this experiment
        pattern = f"{experiment_id}_*.json"
        files = sorted(self.results_dir.glob(pattern))
        
        if not files:
            raise FileNotFoundError(f"No results found for {experiment_id}")
        
        latest_file = files[-1]
        logger.info(f"Loading results from {latest_file}")
        
        with open(latest_file, "r") as f:
            return json.load(f)
    
    def compute_retrieval_metrics(self, result: Dict[str, Any]) -> Dict[str, float]:
        """Compute retrieval metrics from raw results."""
        queries = result["results"]
        
        recall_at_1 = []
        recall_at_5 = []
        recall_at_10 = []
        precision_at_5 = []
        mrr_scores = []
        ndcg_at_5 = []
        
        for query in queries:
            if not query["success"]:
                continue
            
            # Check if we have retrieval metadata
            retrieval_meta = query.get("retrieval_metadata", {})
            retrieved_chunks = retrieval_meta.get("retrieved_chunk_ids", [])
            relevant_chunks = query.get("relevant_chunk_ids", [])
            
            if not relevant_chunks:
                # No ground truth, skip
                continue
            
            relevant_set = set(relevant_chunks)
            
            # Recall@K
            if len(retrieved_chunks) >= 1:
                recall_at_1.append(len(set(retrieved_chunks[:1]) & relevant_set) / len(relevant_set))
            if len(retrieved_chunks) >= 5:
                recall_at_5.append(len(set(retrieved_chunks[:5]) & relevant_set) / len(relevant_set))
            if len(retrieved_chunks) >= 10:
                recall_at_10.append(len(set(retrieved_chunks[:10]) & relevant_set) / len(relevant_set))
            
            # Precision@5
            if len(retrieved_chunks) >= 5:
                precision_at_5.append(len(set(retrieved_chunks[:5]) & relevant_set) / 5)
            
            # MRR
            rr = 0
            for i, chunk_id in enumerate(retrieved_chunks, 1):
                if chunk_id in relevant_set:
                    rr = 1.0 / i
                    break
            mrr_scores.append(rr)
            
            # NDCG@5
            if len(retrieved_chunks) >= 5:
                dcg = 0
                for i, chunk_id in enumerate(retrieved_chunks[:5], 1):
                    rel = 1 if chunk_id in relevant_set else 0
                    dcg += rel / math.log2(i + 1)
                
                # Ideal DCG
                ideal_relevant = min(len(relevant_set), 5)
                idcg = sum(1 / math.log2(i + 1) for i in range(1, ideal_relevant + 1))
                
                ndcg_at_5.append(dcg / idcg if idcg > 0 else 0)
        
        metrics = {
            "recall_at_1": statistics.mean(recall_at_1) if recall_at_1 else 0,
            "recall_at_5": statistics.mean(recall_at_5) if recall_at_5 else 0,
            "recall_at_10": statistics.mean(recall_at_10) if recall_at_10 else 0,
            "precision_at_5": statistics.mean(precision_at_5) if precision_at_5 else 0,
            "mrr": statistics.mean(mrr_scores) if mrr_scores else 0,
            "ndcg_at_5": statistics.mean(ndcg_at_5) if ndcg_at_5 else 0,
        }
        
        return metrics
    
    def compute_generation_metrics(self, result: Dict[str, Any]) -> Dict[str, float]:
        """Compute generation metrics from raw results."""
        queries = result["results"]
        
        answer_correctness = []
        citation_precision = []
        citation_recall = []
        abstention_accuracy = []
        
        for query in queries:
            if not query["success"]:
                continue
            
            response = query["response"]
            expected = query["expected_answer"]
            
            # Answer correctness (simple keyword overlap)
            if expected and response["answer"]:
                expected_words = set(expected.lower().split())
                answer_words = set(response["answer"].lower().split())
                
                if expected_words:
                    overlap = len(expected_words & answer_words) / len(expected_words)
                    answer_correctness.append(overlap)
            
            # Citation metrics
            citations = response.get("citations", [])
            source_doc = query.get("source_document", "")
            
            if citations and source_doc:
                # Citation precision: how many citations are correct
                correct_citations = sum(1 for c in citations if c.get("source") == source_doc)
                citation_precision.append(correct_citations / len(citations))
                
                # Citation recall: did we cite the right source
                cited_sources = set(c.get("source") for c in citations)
                citation_recall.append(1.0 if source_doc in cited_sources else 0.0)
            
            # Abstention accuracy
            is_answerable = query.get("answerable", True)
            abstained = response.get("abstained", False)
            
            if not is_answerable:
                # Should abstain
                abstention_accuracy.append(1.0 if abstained else 0.0)
            else:
                # Should not abstain
                abstention_accuracy.append(0.0 if abstained else 1.0)
        
        metrics = {
            "answer_correctness": statistics.mean(answer_correctness) if answer_correctness else 0,
            "citation_precision": statistics.mean(citation_precision) if citation_precision else 0,
            "citation_recall": statistics.mean(citation_recall) if citation_recall else 0,
            "abstention_accuracy": statistics.mean(abstention_accuracy) if abstention_accuracy else 0,
        }
        
        return metrics
    
    def compute_performance_metrics(self, result: Dict[str, Any]) -> Dict[str, float]:
        """Compute performance metrics from raw results."""
        queries = result["results"]
        
        latencies = [q["latency_ms"] for q in queries if q["success"]]
        
        if not latencies:
            return {
                "latency_p50_ms": 0,
                "latency_p90_ms": 0,
                "latency_p95_ms": 0,
                "latency_p99_ms": 0,
                "throughput_qps": 0,
            }
        
        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)
        
        metrics = {
            "latency_p50_ms": latencies_sorted[n // 2],
            "latency_p90_ms": latencies_sorted[int(n * 0.90)],
            "latency_p95_ms": latencies_sorted[int(n * 0.95)],
            "latency_p99_ms": latencies_sorted[int(n * 0.99)],
            "throughput_qps": 1000.0 / statistics.mean(latencies) if latencies else 0,
        }
        
        return metrics
    
    def compute_confidence_interval(self, values: List[float], confidence: float = 0.95) -> Tuple[float, float, float]:
        """Compute confidence interval for a list of values."""
        if not values:
            return (0, 0, 0)
        
        n = len(values)
        mean = statistics.mean(values)
        
        if n < 2:
            return (mean, mean, mean)
        
        stdev = statistics.stdev(values)
        
        # For 95% CI, use z=1.96
        z = 1.96 if confidence == 0.95 else 2.576  # 2.576 for 99%
        
        margin = z * stdev / math.sqrt(n)
        
        return (mean - margin, mean, mean + margin)
    
    def analyze_experiment(self, experiment_id: str) -> Dict[str, Any]:
        """Analyze a single experiment."""
        logger.info(f"Analyzing {experiment_id}")
        
        result = self.load_experiment_results(experiment_id)
        
        # Compute metrics
        retrieval_metrics = self.compute_retrieval_metrics(result)
        generation_metrics = self.compute_generation_metrics(result)
        performance_metrics = self.compute_performance_metrics(result)
        
        analysis = {
            "experiment_id": experiment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "total_queries": result["total_questions"],
            "successful_queries": result["successful_queries"],
            "failed_queries": result["failed_queries"],
            "retrieval_metrics": retrieval_metrics,
            "generation_metrics": generation_metrics,
            "performance_metrics": performance_metrics,
            "summary": {
                "avg_latency_ms": result["avg_latency_ms"],
                "total_time_seconds": result["total_time_seconds"],
            }
        }
        
        return analysis
    
    def save_analysis(self, analysis: Dict[str, Any]) -> Path:
        """Save analysis results."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{analysis['experiment_id']}_analysis_{timestamp}.json"
        filepath = self.analysis_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Analysis saved to {filepath}")
        return filepath
    
    def compare_experiments(self, experiment_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple experiments."""
        logger.info(f"Comparing {len(experiment_ids)} experiments")
        
        analyses = []
        for exp_id in experiment_ids:
            try:
                analysis = self.analyze_experiment(exp_id)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze {exp_id}: {e}")
        
        comparison = {
            "timestamp": datetime.utcnow().isoformat(),
            "experiments": analyses,
            "comparison": {}
        }
        
        # Compare metrics across experiments
        if len(analyses) >= 2:
            # Find best performing experiment for each metric
            metrics_to_compare = [
                "retrieval_metrics.recall_at_5",
                "retrieval_metrics.precision_at_5",
                "retrieval_metrics.mrr",
                "generation_metrics.answer_correctness",
                "generation_metrics.citation_precision",
                "performance_metrics.latency_p50_ms",
            ]
            
            for metric_path in metrics_to_compare:
                values = []
                for analysis in analyses:
                    # Navigate nested dict
                    parts = metric_path.split(".")
                    value = analysis
                    for part in parts:
                        value = value.get(part, {})
                    
                    if isinstance(value, (int, float)):
                        values.append((analysis["experiment_id"], value))
                
                if values:
                    if "latency" in metric_path:
                        # Lower is better
                        best = min(values, key=lambda x: x[1])
                    else:
                        # Higher is better
                        best = max(values, key=lambda x: x[1])
                    
                    comparison["comparison"][metric_path] = {
                        "best_experiment": best[0],
                        "best_value": best[1],
                    }
        
        return comparison
    
    def analyze_all(self):
        """Analyze all experiments."""
        # Find all experiment result files
        result_files = list(self.results_dir.glob("EXP-*_*.json"))
        
        if not result_files:
            logger.warning("No experiment results found")
            return
        
        # Group by experiment ID
        experiments = {}
        for f in result_files:
            exp_id = f.stem.rsplit("_", 1)[0]
            if exp_id not in experiments:
                experiments[exp_id] = []
            experiments[exp_id].append(f)
        
        # Analyze each experiment
        analyses = []
        for exp_id in experiments.keys():
            try:
                analysis = self.analyze_experiment(exp_id)
                analyses.append(analysis)
            except Exception as e:
                logger.error(f"Failed to analyze {exp_id}: {e}")
        
        # Compare experiments
        if len(analyses) >= 2:
            comparison = self.compare_experiments([a["experiment_id"] for a in analyses])
            
            # Save comparison
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            comparison_file = self.analysis_dir / f"comparison_{timestamp}.json"
            with open(comparison_file, "w") as f:
                json.dump(comparison, f, indent=2)
            
            logger.info(f"Comparison saved to {comparison_file}")
        
        return analyses


def main():
    """Main entry point."""
    analyzer = ExperimentAnalyzer()
    analyzer.analyze_all()


if __name__ == "__main__":
    main()
