#!/usr/bin/env python3
"""
Performance measurement and profiling tool for RAG Pipeline.

Measures:
- Latency at each pipeline stage
- Throughput (queries/second)
- Memory usage
- Token usage and costs
- Scalability metrics
"""

import time
import json
import psutil
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import statistics

from src.pipeline import RAGPipeline
from src.core.config import config


class PerformanceProfiler:
    """Comprehensive performance profiling for RAG pipeline."""
    
    def __init__(self, output_dir: str = "performance_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.pipeline = RAGPipeline()
        self.measurements = []
        
    def measure_query_latency(self, query: str, num_runs: int = 10) -> Dict[str, Any]:
        """
        Measure query latency across multiple runs.
        
        Returns:
            Dictionary with mean, median, p95, p99, min, max latencies
        """
        latencies = []
        stage_latencies = {
            'query_analysis': [],
            'retrieval': [],
            'evidence_assessment': [],
            'generation': [],
            'citation_validation': [],
            'total': []
        }
        
        for i in range(num_runs):
            start = time.perf_counter()
            
            # Run query with tracing
            response = self.pipeline.query(query)
            
            total_time = (time.perf_counter() - start) * 1000  # ms
            latencies.append(total_time)
            stage_latencies['total'].append(total_time)
            
            # Extract stage latencies from trace if available
            if hasattr(response, 'latency_breakdown'):
                for stage, latency in response.latency_breakdown.items():
                    if stage in stage_latencies:
                        stage_latencies[stage].append(latency)
        
        # Calculate statistics
        results = {
            'query': query,
            'num_runs': num_runs,
            'latency_ms': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'stdev': statistics.stdev(latencies) if len(latencies) > 1 else 0,
                'min': min(latencies),
                'max': max(latencies),
                'p95': self._percentile(latencies, 95),
                'p99': self._percentile(latencies, 99)
            },
            'stage_latencies_ms': {}
        }
        
        for stage, times in stage_latencies.items():
            if times:
                results['stage_latencies_ms'][stage] = {
                    'mean': statistics.mean(times),
                    'median': statistics.median(times),
                    'p95': self._percentile(times, 95)
                }
        
        return results
    
    def measure_throughput(self, queries: List[str], duration_seconds: int = 60) -> Dict[str, Any]:
        """
        Measure throughput (queries per second) over a time period.
        """
        start_time = time.perf_counter()
        query_count = 0
        query_idx = 0
        
        while (time.perf_counter() - start_time) < duration_seconds:
            query = queries[query_idx % len(queries)]
            self.pipeline.query(query)
            query_count += 1
            query_idx += 1
        
        elapsed = time.perf_counter() - start_time
        
        return {
            'duration_seconds': elapsed,
            'queries_processed': query_count,
            'throughput_qps': query_count / elapsed,
            'avg_latency_ms': (elapsed * 1000) / query_count
        }
    
    def measure_memory_usage(self) -> Dict[str, Any]:
        """Measure current memory usage."""
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
            'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
            'percent': process.memory_percent()
        }
    
    def measure_ingestion_performance(self, pdf_paths: List[Path]) -> Dict[str, Any]:
        """
        Measure document ingestion performance.
        """
        results = {
            'documents': [],
            'total_time_ms': 0,
            'avg_time_per_doc_ms': 0
        }
        
        start = time.perf_counter()
        
        for pdf_path in pdf_paths:
            doc_start = time.perf_counter()
            
            # Ingest document
            self.pipeline.ingest_document(str(pdf_path))
            
            doc_time = (time.perf_counter() - doc_start) * 1000
            results['documents'].append({
                'filename': pdf_path.name,
                'time_ms': doc_time,
                'size_mb': pdf_path.stat().st_size / 1024 / 1024
            })
        
        total_time = (time.perf_counter() - start) * 1000
        results['total_time_ms'] = total_time
        results['avg_time_per_doc_ms'] = total_time / len(pdf_paths) if pdf_paths else 0
        
        return results
    
    def measure_scalability(self, num_documents: List[int]) -> Dict[str, Any]:
        """
        Measure how performance scales with corpus size.
        
        Args:
            num_documents: List of corpus sizes to test (e.g., [10, 50, 100, 500])
        """
        results = []
        
        for num_docs in num_documents:
            # Clear existing index
            self.pipeline.clear_indexes()
            
            # Ingest num_docs documents (assuming we have test documents)
            # For now, we'll simulate this
            ingestion_start = time.perf_counter()
            # TODO: Actually ingest num_docs documents
            ingestion_time = (time.perf_counter() - ingestion_start) * 1000
            
            # Measure query latency
            test_query = "What was the revenue in 2023?"
            latency_result = self.measure_query_latency(test_query, num_runs=5)
            
            # Measure memory
            memory = self.measure_memory_usage()
            
            results.append({
                'num_documents': num_docs,
                'ingestion_time_ms': ingestion_time,
                'query_latency_ms': latency_result['latency_ms'],
                'memory_mb': memory['rss_mb']
            })
        
        return results
    
    def measure_cost(self, num_queries: int = 100) -> Dict[str, Any]:
        """
        Estimate API costs for queries.
        
        Note: This is an estimate based on typical token usage.
        Actual costs depend on the LLM provider and pricing.
        """
        # Estimate token usage per query
        avg_input_tokens = 1500  # Context + query
        avg_output_tokens = 200  # Answer
        
        # GPT-4o-mini pricing (as of 2024)
        input_cost_per_1k = 0.00015  # $0.15 per 1M tokens
        output_cost_per_1k = 0.0006  # $0.60 per 1M tokens
        
        total_input_tokens = avg_input_tokens * num_queries
        total_output_tokens = avg_output_tokens * num_queries
        
        input_cost = (total_input_tokens / 1000) * input_cost_per_1k
        output_cost = (total_output_tokens / 1000) * output_cost_per_1k
        
        return {
            'num_queries': num_queries,
            'avg_input_tokens': avg_input_tokens,
            'avg_output_tokens': avg_output_tokens,
            'total_input_tokens': total_input_tokens,
            'total_output_tokens': total_output_tokens,
            'estimated_cost_usd': input_cost + output_cost,
            'cost_per_query_usd': (input_cost + output_cost) / num_queries
        }
    
    def run_comprehensive_benchmark(self, test_queries: List[str]) -> Dict[str, Any]:
        """
        Run a comprehensive performance benchmark.
        """
        print("Running comprehensive performance benchmark...")
        
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'config': {
                'chunk_size': config.chunking.chunk_size,
                'chunk_overlap': config.chunking.chunk_overlap,
                'retrieval_top_k': config.retrieval.top_k,
                'rerank_enabled': config.retrieval.rerank_enabled,
                'evidence_check_enabled': config.evidence.check_enabled
            },
            'latency_tests': [],
            'throughput_test': None,
            'memory_usage': None,
            'cost_estimate': None
        }
        
        # Test latency for each query
        print("\n1. Measuring query latency...")
        for query in test_queries:
            print(f"   Testing: {query[:50]}...")
            latency_result = self.measure_query_latency(query, num_runs=10)
            results['latency_tests'].append(latency_result)
        
        # Test throughput
        print("\n2. Measuring throughput...")
        results['throughput_test'] = self.measure_throughput(test_queries, duration_seconds=30)
        
        # Measure memory
        print("\n3. Measuring memory usage...")
        results['memory_usage'] = self.measure_memory_usage()
        
        # Estimate cost
        print("\n4. Estimating costs...")
        results['cost_estimate'] = self.measure_cost(num_queries=100)
        
        # Save results
        output_file = self.output_dir / f"benchmark_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return results
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        k = (len(sorted_data) - 1) * (percentile / 100)
        f = int(k)
        c = f + 1 if f + 1 < len(sorted_data) else f
        d = k - f
        return sorted_data[f] + d * (sorted_data[c] - sorted_data[f])
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable performance report."""
        report = []
        report.append("=" * 80)
        report.append("RAG PIPELINE PERFORMANCE REPORT")
        report.append("=" * 80)
        report.append(f"\nTimestamp: {results['timestamp']}")
        report.append(f"\nConfiguration:")
        for key, value in results['config'].items():
            report.append(f"  {key}: {value}")
        
        report.append("\n" + "=" * 80)
        report.append("LATENCY TESTS")
        report.append("=" * 80)
        
        for test in results['latency_tests']:
            report.append(f"\nQuery: {test['query']}")
            report.append(f"  Mean: {test['latency_ms']['mean']:.2f} ms")
            report.append(f"  Median: {test['latency_ms']['median']:.2f} ms")
            report.append(f"  P95: {test['latency_ms']['p95']:.2f} ms")
            report.append(f"  P99: {test['latency_ms']['p99']:.2f} ms")
            
            if test['stage_latencies_ms']:
                report.append("  Stage breakdown:")
                for stage, stats in test['stage_latencies_ms'].items():
                    report.append(f"    {stage}: {stats['mean']:.2f} ms (median: {stats['median']:.2f} ms)")
        
        report.append("\n" + "=" * 80)
        report.append("THROUGHPUT TEST")
        report.append("=" * 80)
        throughput = results['throughput_test']
        report.append(f"  Duration: {throughput['duration_seconds']:.2f} seconds")
        report.append(f"  Queries processed: {throughput['queries_processed']}")
        report.append(f"  Throughput: {throughput['throughput_qps']:.2f} queries/second")
        report.append(f"  Avg latency: {throughput['avg_latency_ms']:.2f} ms")
        
        report.append("\n" + "=" * 80)
        report.append("MEMORY USAGE")
        report.append("=" * 80)
        memory = results['memory_usage']
        report.append(f"  RSS: {memory['rss_mb']:.2f} MB")
        report.append(f"  VMS: {memory['vms_mb']:.2f} MB")
        report.append(f"  Percent: {memory['percent']:.2f}%")
        
        report.append("\n" + "=" * 80)
        report.append("COST ESTIMATE")
        report.append("=" * 80)
        cost = results['cost_estimate']
        report.append(f"  Queries: {cost['num_queries']}")
        report.append(f"  Avg input tokens: {cost['avg_input_tokens']}")
        report.append(f"  Avg output tokens: {cost['avg_output_tokens']}")
        report.append(f"  Total cost: ${cost['estimated_cost_usd']:.4f}")
        report.append(f"  Cost per query: ${cost['cost_per_query_usd']:.6f}")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


def main():
    """Run performance benchmark from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Pipeline Performance Profiler")
    parser.add_argument('--output', type=str, default='performance_results',
                       help='Output directory for results')
    parser.add_argument('--queries', type=str, nargs='+',
                       default=[
                           "What was the revenue in 2023?",
                           "Compare Q1 and Q2 results",
                           "What is the company's strategy?",
                           "How did operating margin change?",
                           "What were the risk factors?"
                       ],
                       help='Test queries')
    
    args = parser.parse_args()
    
    profiler = PerformanceProfiler(output_dir=args.output)
    results = profiler.run_comprehensive_benchmark(args.queries)
    
    # Generate and print report
    report = profiler.generate_report(results)
    print("\n" + report)
    
    # Save report
    report_file = Path(args.output) / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
