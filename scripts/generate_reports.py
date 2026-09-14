#!/usr/bin/env python3
"""
Generate comprehensive reports from experiment analysis.

This script creates human-readable reports summarizing:
- Experiment results
- Metric comparisons
- Statistical analysis
- Key findings
- Recommendations
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate reports from experiment analysis."""
    
    def __init__(self, analysis_dir: str = "experiments/analysis"):
        self.analysis_dir = Path(analysis_dir)
        self.reports_dir = Path("experiments/reports")
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def load_analysis(self, experiment_id: str) -> Dict[str, Any]:
        """Load analysis results."""
        pattern = f"{experiment_id}_analysis_*.json"
        files = sorted(self.analysis_dir.glob(pattern))
        
        if not files:
            raise FileNotFoundError(f"No analysis found for {experiment_id}")
        
        latest_file = files[-1]
        
        with open(latest_file, "r") as f:
            return json.load(f)
    
    def load_comparison(self) -> Dict[str, Any]:
        """Load comparison results."""
        pattern = "comparison_*.json"
        files = sorted(self.analysis_dir.glob(pattern))
        
        if not files:
            raise FileNotFoundError("No comparison found")
        
        latest_file = files[-1]
        
        with open(latest_file, "r") as f:
            return json.load(f)
    
    def generate_experiment_report(self, experiment_id: str) -> str:
        """Generate report for a single experiment."""
        analysis = self.load_analysis(experiment_id)
        
        report = []
        report.append(f"# Experiment Report: {experiment_id}")
        report.append(f"\n**Generated:** {datetime.utcnow().isoformat()}")
        report.append(f"\n---\n")
        
        # Summary
        report.append("## Summary\n")
        report.append(f"- **Total Queries:** {analysis['total_queries']}")
        report.append(f"- **Successful:** {analysis['successful_queries']}")
        report.append(f"- **Failed:** {analysis['failed_queries']}")
        report.append(f"- **Success Rate:** {analysis['successful_queries'] / analysis['total_queries'] * 100:.1f}%")
        report.append(f"- **Average Latency:** {analysis['summary']['avg_latency_ms']:.2f}ms")
        report.append(f"- **Total Time:** {analysis['summary']['total_time_seconds']:.2f}s")
        
        # Retrieval Metrics
        report.append("\n## Retrieval Metrics\n")
        retrieval = analysis['retrieval_metrics']
        report.append(f"- **Recall@1:** {retrieval['recall_at_1']:.4f}")
        report.append(f"- **Recall@5:** {retrieval['recall_at_5']:.4f}")
        report.append(f"- **Recall@10:** {retrieval['recall_at_10']:.4f}")
        report.append(f"- **Precision@5:** {retrieval['precision_at_5']:.4f}")
        report.append(f"- **MRR:** {retrieval['mrr']:.4f}")
        report.append(f"- **NDCG@5:** {retrieval['ndcg_at_5']:.4f}")
        
        # Generation Metrics
        report.append("\n## Generation Metrics\n")
        generation = analysis['generation_metrics']
        report.append(f"- **Answer Correctness:** {generation['answer_correctness']:.4f}")
        report.append(f"- **Citation Precision:** {generation['citation_precision']:.4f}")
        report.append(f"- **Citation Recall:** {generation['citation_recall']:.4f}")
        report.append(f"- **Abstention Accuracy:** {generation['abstention_accuracy']:.4f}")
        
        # Performance Metrics
        report.append("\n## Performance Metrics\n")
        performance = analysis['performance_metrics']
        report.append(f"- **Latency P50:** {performance['latency_p50_ms']:.2f}ms")
        report.append(f"- **Latency P90:** {performance['latency_p90_ms']:.2f}ms")
        report.append(f"- **Latency P95:** {performance['latency_p95_ms']:.2f}ms")
        report.append(f"- **Latency P99:** {performance['latency_p99_ms']:.2f}ms")
        report.append(f"- **Throughput:** {performance['throughput_qps']:.2f} queries/sec")
        
        return "\n".join(report)
    
    def generate_comparison_report(self) -> str:
        """Generate comparison report across experiments."""
        comparison = self.load_comparison()
        
        report = []
        report.append("# Experiment Comparison Report")
        report.append(f"\n**Generated:** {datetime.utcnow().isoformat()}")
        report.append(f"\n---\n")
        
        # Summary
        report.append("## Summary\n")
        report.append(f"**Experiments Compared:** {len(comparison['experiments'])}")
        report.append(f"\n")
        
        # Experiment Overview
        report.append("## Experiment Overview\n")
        report.append("| Experiment | Success Rate | Avg Latency | Recall@5 | Precision@5 | MRR |")
        report.append("|------------|--------------|-------------|----------|-------------|-----|")
        
        for exp in comparison['experiments']:
            success_rate = exp['successful_queries'] / exp['total_queries'] * 100
            report.append(
                f"| {exp['experiment_id']} | "
                f"{success_rate:.1f}% | "
                f"{exp['summary']['avg_latency_ms']:.2f}ms | "
                f"{exp['retrieval_metrics']['recall_at_5']:.4f} | "
                f"{exp['retrieval_metrics']['precision_at_5']:.4f} | "
                f"{exp['retrieval_metrics']['mrr']:.4f} |"
            )
        
        # Best Performers
        report.append("\n## Best Performers\n")
        
        comparisons = comparison.get('comparison', {})
        
        if 'retrieval_metrics.recall_at_5' in comparisons:
            best = comparisons['retrieval_metrics.recall_at_5']
            report.append(f"- **Best Recall@5:** {best['best_experiment']} ({best['best_value']:.4f})")
        
        if 'retrieval_metrics.precision_at_5' in comparisons:
            best = comparisons['retrieval_metrics.precision_at_5']
            report.append(f"- **Best Precision@5:** {best['best_experiment']} ({best['best_value']:.4f})")
        
        if 'retrieval_metrics.mrr' in comparisons:
            best = comparisons['retrieval_metrics.mrr']
            report.append(f"- **Best MRR:** {best['best_experiment']} ({best['best_value']:.4f})")
        
        if 'generation_metrics.answer_correctness' in comparisons:
            best = comparisons['generation_metrics.answer_correctness']
            report.append(f"- **Best Answer Correctness:** {best['best_experiment']} ({best['best_value']:.4f})")
        
        if 'generation_metrics.citation_precision' in comparisons:
            best = comparisons['generation_metrics.citation_precision']
            report.append(f"- **Best Citation Precision:** {best['best_experiment']} ({best['best_value']:.4f})")
        
        if 'performance_metrics.latency_p50_ms' in comparisons:
            best = comparisons['performance_metrics.latency_p50_ms']
            report.append(f"- **Lowest Latency:** {best['best_experiment']} ({best['best_value']:.2f}ms)")
        
        # Key Findings
        report.append("\n## Key Findings\n")
        
        # Analyze tradeoffs
        if len(comparison['experiments']) >= 2:
            # Find best retrieval vs best performance
            best_recall_exp = max(comparison['experiments'], 
                                 key=lambda x: x['retrieval_metrics']['recall_at_5'])
            best_perf_exp = min(comparison['experiments'], 
                               key=lambda x: x['performance_metrics']['latency_p50_ms'])
            
            report.append("### Tradeoffs\n")
            report.append(f"- **Best Retrieval Quality:** {best_recall_exp['experiment_id']}")
            report.append(f"  - Recall@5: {best_recall_exp['retrieval_metrics']['recall_at_5']:.4f}")
            report.append(f"  - Latency: {best_recall_exp['performance_metrics']['latency_p50_ms']:.2f}ms")
            report.append(f"\n- **Best Performance:** {best_perf_exp['experiment_id']}")
            report.append(f"  - Latency: {best_perf_exp['performance_metrics']['latency_p50_ms']:.2f}ms")
            report.append(f"  - Recall@5: {best_perf_exp['retrieval_metrics']['recall_at_5']:.4f}")
            
            # Calculate quality/performance ratio
            report.append("\n### Quality vs Performance\n")
            for exp in comparison['experiments']:
                quality = exp['retrieval_metrics']['recall_at_5']
                latency = exp['performance_metrics']['latency_p50_ms']
                ratio = quality / latency * 1000 if latency > 0 else 0
                report.append(f"- **{exp['experiment_id']}:** {ratio:.4f} (quality/latency ratio)")
        
        # Recommendations
        report.append("\n## Recommendations\n")
        
        if comparisons:
            best_overall = max(comparison['experiments'], 
                              key=lambda x: (x['retrieval_metrics']['recall_at_5'] + 
                                           x['generation_metrics']['answer_correctness']) / 2)
            
            report.append(f"### Best Overall System\n")
            report.append(f"**{best_overall['experiment_id']}** provides the best balance of:")
            report.append(f"- Retrieval quality (Recall@5: {best_overall['retrieval_metrics']['recall_at_5']:.4f})")
            report.append(f"- Answer correctness ({best_overall['generation_metrics']['answer_correctness']:.4f})")
            report.append(f"- Performance ({best_overall['performance_metrics']['latency_p50_ms']:.2f}ms)")
        
        return "\n".join(report)
    
    def generate_summary_report(self) -> str:
        """Generate executive summary report."""
        comparison = self.load_comparison()
        
        report = []
        report.append("# RAG Pipeline - Executive Summary")
        report.append(f"\n**Generated:** {datetime.utcnow().isoformat()}")
        report.append(f"\n---\n")
        
        # Overview
        report.append("## Overview\n")
        report.append(f"This report summarizes the evaluation of the RAG Pipeline system across ")
        report.append(f"{len(comparison['experiments'])} experimental configurations.\n")
        
        # Key Metrics
        report.append("\n## Key Metrics\n")
        
        # Find best performing experiment
        best_exp = max(comparison['experiments'], 
                      key=lambda x: x['retrieval_metrics']['recall_at_5'])
        
        report.append(f"### Best Performing Configuration: {best_exp['experiment_id']}\n")
        report.append(f"- **Retrieval Quality:**")
        report.append(f"  - Recall@5: {best_exp['retrieval_metrics']['recall_at_5']:.4f}")
        report.append(f"  - Precision@5: {best_exp['retrieval_metrics']['precision_at_5']:.4f}")
        report.append(f"  - MRR: {best_exp['retrieval_metrics']['mrr']:.4f}")
        report.append(f"\n- **Generation Quality:**")
        report.append(f"  - Answer Correctness: {best_exp['generation_metrics']['answer_correctness']:.4f}")
        report.append(f"  - Citation Precision: {best_exp['generation_metrics']['citation_precision']:.4f}")
        report.append(f"\n- **Performance:**")
        report.append(f"  - Latency (P50): {best_exp['performance_metrics']['latency_p50_ms']:.2f}ms")
        report.append(f"  - Throughput: {best_exp['performance_metrics']['throughput_qps']:.2f} queries/sec")
        
        # Findings
        report.append("\n## Key Findings\n")
        
        # Analyze adaptive vs fixed
        adaptive_exps = [e for e in comparison['experiments'] if 'adaptive' in e['experiment_id']]
        fixed_exps = [e for e in comparison['experiments'] if 'adaptive' not in e['experiment_id']]
        
        if adaptive_exps and fixed_exps:
            avg_adaptive_recall = sum(e['retrieval_metrics']['recall_at_5'] for e in adaptive_exps) / len(adaptive_exps)
            avg_fixed_recall = sum(e['retrieval_metrics']['recall_at_5'] for e in fixed_exps) / len(fixed_exps)
            
            improvement = ((avg_adaptive_recall - avg_fixed_recall) / avg_fixed_recall * 100) if avg_fixed_recall > 0 else 0
            
            report.append(f"### Adaptive Retrieval Impact\n")
            report.append(f"- **Fixed Retrieval Avg Recall@5:** {avg_fixed_recall:.4f}")
            report.append(f"- **Adaptive Retrieval Avg Recall@5:** {avg_adaptive_recall:.4f}")
            report.append(f"- **Improvement:** {improvement:+.2f}%")
            
            if improvement > 0:
                report.append(f"\n✅ **Adaptive retrieval improves retrieval quality**")
            else:
                report.append(f"\n⚠️ **Adaptive retrieval does not improve retrieval quality**")
        
        # Analyze reranking impact
        rerank_exps = [e for e in comparison['experiments'] if 'rerank' in e['experiment_id']]
        no_rerank_exps = [e for e in comparison['experiments'] if 'rerank' not in e['experiment_id']]
        
        if rerank_exps and no_rerank_exps:
            avg_rerank_precision = sum(e['retrieval_metrics']['precision_at_5'] for e in rerank_exps) / len(rerank_exps)
            avg_no_rerank_precision = sum(e['retrieval_metrics']['precision_at_5'] for e in no_rerank_exps) / len(no_rerank_exps)
            
            improvement = ((avg_rerank_precision - avg_no_rerank_precision) / avg_no_rerank_precision * 100) if avg_no_rerank_precision > 0 else 0
            
            report.append(f"\n### Reranking Impact\n")
            report.append(f"- **Without Reranking Avg Precision@5:** {avg_no_rerank_precision:.4f}")
            report.append(f"- **With Reranking Avg Precision@5:** {avg_rerank_precision:.4f}")
            report.append(f"- **Improvement:** {improvement:+.2f}%")
            
            if improvement > 0:
                report.append(f"\n✅ **Reranking improves precision**")
            else:
                report.append(f"\n⚠️ **Reranking does not improve precision**")
        
        # Conclusions
        report.append("\n## Conclusions\n")
        
        report.append(f"The RAG Pipeline demonstrates ")
        
        if adaptive_exps and fixed_exps:
            if avg_adaptive_recall > avg_fixed_recall:
                report.append(f"strong adaptive retrieval capabilities, ")
            else:
                report.append(f"baseline retrieval capabilities, ")
        
        if rerank_exps and no_rerank_exps:
            if avg_rerank_precision > avg_no_rerank_precision:
                report.append(f"effective reranking, ")
            else:
                report.append(f"limited reranking benefit, ")
        
        report.append(f"with the best configuration achieving:\n")
        report.append(f"- Recall@5: {best_exp['retrieval_metrics']['recall_at_5']:.4f}")
        report.append(f"- Answer Correctness: {best_exp['generation_metrics']['answer_correctness']:.4f}")
        report.append(f"- Latency: {best_exp['performance_metrics']['latency_p50_ms']:.2f}ms")
        
        # Limitations
        report.append("\n## Limitations\n")
        report.append("- Benchmark uses sample documents, not real SEC filings")
        report.append("- Answer correctness uses simple keyword overlap")
        report.append("- No LLM-as-judge evaluation")
        report.append("- Limited to 210 benchmark questions")
        
        # Next Steps
        report.append("\n## Next Steps\n")
        report.append("1. Download real SEC filings from EDGAR")
        report.append("2. Expand benchmark to 500+ questions")
        report.append("3. Implement LLM-as-judge for semantic evaluation")
        report.append("4. Add multi-hop and temporal reasoning tests")
        report.append("5. Conduct user study for real-world validation")
        
        return "\n".join(report)
    
    def generate_all_reports(self):
        """Generate all reports."""
        logger.info("Generating reports...")
        
        # Find all experiments
        analysis_files = list(self.analysis_dir.glob("EXP-*_analysis_*.json"))
        
        if not analysis_files:
            logger.warning("No analysis files found")
            return
        
        # Generate individual experiment reports
        for analysis_file in analysis_files:
            exp_id = analysis_file.stem.rsplit("_analysis", 1)[0]
            
            try:
                report = self.generate_experiment_report(exp_id)
                
                # Save report
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                report_file = self.reports_dir / f"{exp_id}_report_{timestamp}.md"
                
                with open(report_file, "w") as f:
                    f.write(report)
                
                logger.info(f"Generated report: {report_file}")
                
            except Exception as e:
                logger.error(f"Failed to generate report for {exp_id}: {e}")
        
        # Generate comparison report
        try:
            comparison_report = self.generate_comparison_report()
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            comparison_file = self.reports_dir / f"comparison_report_{timestamp}.md"
            
            with open(comparison_file, "w") as f:
                f.write(comparison_report)
            
            logger.info(f"Generated comparison report: {comparison_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate comparison report: {e}")
        
        # Generate summary report
        try:
            summary_report = self.generate_summary_report()
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            summary_file = self.reports_dir / f"summary_report_{timestamp}.md"
            
            with open(summary_file, "w") as f:
                f.write(summary_report)
            
            logger.info(f"Generated summary report: {summary_file}")
            
        except Exception as e:
            logger.error(f"Failed to generate summary report: {e}")


def main():
    """Main entry point."""
    generator = ReportGenerator()
    generator.generate_all_reports()


if __name__ == "__main__":
    main()
