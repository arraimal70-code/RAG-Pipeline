#!/usr/bin/env python3
"""
Scalability testing framework for RAG Pipeline.

Tests:
- Performance at different corpus sizes
- Memory usage scaling
- Query latency at scale
- Indexing time scaling
- Concurrent query handling
"""

import time
import json
import psutil
import os
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import statistics

from src.pipeline import RAGPipeline


class ScalabilityTester:
    """Test system scalability at different scales."""
    
    def __init__(self, output_dir: str = "scalability_results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.pipeline = RAGPipeline()
        
    def test_corpus_scaling(
        self,
        corpus_sizes: List[int],
        test_query: str = "What was the revenue in 2023?"
    ) -> Dict[str, Any]:
        """
        Test how performance scales with corpus size.
        
        Args:
            corpus_sizes: List of corpus sizes to test (number of documents)
            test_query: Query to use for testing
        
        Returns:
            Dictionary with scaling metrics
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'test_query': test_query,
            'corpus_sizes': [],
            'metrics': []
        }
        
        for num_docs in corpus_sizes:
            print(f"\nTesting corpus size: {num_docs} documents")
            
            # Clear existing index
            self.pipeline.clear_indexes()
            
            # Generate and ingest test documents
            ingestion_start = time.perf_counter()
            self._generate_and_ingest_documents(num_docs)
            ingestion_time = (time.perf_counter() - ingestion_start) * 1000
            
            # Measure query latency
            latencies = []
            for i in range(10):
                start = time.perf_counter()
                response = self.pipeline.query(test_query)
                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)
            
            # Measure memory usage
            process = psutil.Process(os.getpid())
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            # Get index size
            index_size = self._get_index_size()
            
            metrics = {
                'num_documents': num_docs,
                'ingestion_time_ms': ingestion_time,
                'query_latency_ms': {
                    'mean': statistics.mean(latencies),
                    'median': statistics.median(latencies),
                    'p95': self._percentile(latencies, 95),
                    'min': min(latencies),
                    'max': max(latencies)
                },
                'memory_mb': memory_mb,
                'index_size_mb': index_size
            }
            
            results['corpus_sizes'].append(num_docs)
            results['metrics'].append(metrics)
            
            print(f"  Ingestion: {ingestion_time:.2f} ms")
            print(f"  Query latency: {statistics.mean(latencies):.2f} ms (mean)")
            print(f"  Memory: {memory_mb:.2f} MB")
            print(f"  Index size: {index_size:.2f} MB")
        
        # Save results
        output_file = self.output_dir / f"scaling_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        return results
    
    def test_concurrent_queries(
        self,
        num_concurrent: int = 10,
        test_query: str = "What was the revenue?"
    ) -> Dict[str, Any]:
        """
        Test handling of concurrent queries.
        
        Args:
            num_concurrent: Number of concurrent queries to simulate
            test_query: Query to use
        
        Returns:
            Dictionary with concurrency metrics
        """
        import concurrent.futures
        
        print(f"\nTesting {num_concurrent} concurrent queries")
        
        # Ensure we have some documents
        if self.pipeline.get_index_size() == 0:
            self._generate_and_ingest_documents(50)
        
        def run_query(query_id: int):
            start = time.perf_counter()
            response = self.pipeline.query(test_query)
            latency = (time.perf_counter() - start) * 1000
            return {
                'query_id': query_id,
                'latency_ms': latency,
                'success': response is not None
            }
        
        # Run concurrent queries
        start = time.perf_counter()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(run_query, i) for i in range(num_concurrent)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        total_time = (time.perf_counter() - start) * 1000
        
        # Calculate metrics
        latencies = [r['latency_ms'] for r in results]
        success_count = sum(1 for r in results if r['success'])
        
        metrics = {
            'num_concurrent': num_concurrent,
            'total_time_ms': total_time,
            'success_rate': success_count / num_concurrent,
            'latency_ms': {
                'mean': statistics.mean(latencies),
                'median': statistics.median(latencies),
                'p95': self._percentile(latencies, 95),
                'min': min(latencies),
                'max': max(latencies)
            },
            'throughput_qps': num_concurrent / (total_time / 1000)
        }
        
        print(f"  Total time: {total_time:.2f} ms")
        print(f"  Success rate: {metrics['success_rate']:.2%}")
        print(f"  Mean latency: {metrics['latency_ms']['mean']:.2f} ms")
        print(f"  Throughput: {metrics['throughput_qps']:.2f} queries/sec")
        
        return metrics
    
    def test_memory_scaling(
        self,
        corpus_sizes: List[int]
    ) -> Dict[str, Any]:
        """
        Test memory usage at different scales.
        
        Args:
            corpus_sizes: List of corpus sizes to test
        
        Returns:
            Dictionary with memory metrics
        """
        results = {
            'timestamp': datetime.utcnow().isoformat(),
            'metrics': []
        }
        
        process = psutil.Process(os.getpid())
        
        for num_docs in corpus_sizes:
            print(f"\nTesting memory at {num_docs} documents")
            
            # Clear and rebuild
            self.pipeline.clear_indexes()
            
            # Measure baseline memory
            baseline_memory = process.memory_info().rss / 1024 / 1024
            
            # Ingest documents
            self._generate_and_ingest_documents(num_docs)
            
            # Measure memory after ingestion
            after_memory = process.memory_info().rss / 1024 / 1024
            
            metrics = {
                'num_documents': num_docs,
                'baseline_memory_mb': baseline_memory,
                'after_memory_mb': after_memory,
                'memory_increase_mb': after_memory - baseline_memory,
                'memory_per_doc_kb': (after_memory - baseline_memory) * 1024 / num_docs if num_docs > 0 else 0
            }
            
            results['metrics'].append(metrics)
            
            print(f"  Baseline: {baseline_memory:.2f} MB")
            print(f"  After: {after_memory:.2f} MB")
            print(f"  Increase: {metrics['memory_increase_mb']:.2f} MB")
            print(f"  Per document: {metrics['memory_per_doc_kb']:.2f} KB")
        
        return results
    
    def _generate_and_ingest_documents(self, num_docs: int):
        """Generate and ingest test documents."""
        import tempfile
        
        for i in range(num_docs):
            # Generate test document content
            content = f"""
Financial Report Q{i % 4 + 1} 2023

Revenue: ${100 + i} million
Operating Income: ${20 + i // 10} million
Net Income: ${15 + i // 10} million

The company reported strong performance in Q{i % 4 + 1} 2023,
with revenue growth of {5 + i % 10}% compared to the previous quarter.

Key highlights:
- Product sales increased by {8 + i % 5}%
- Service revenue grew by {12 + i % 8}%
- Operating margin improved to {20 + i % 5}%
"""
            
            # Write to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                # Ingest document
                self.pipeline.ingest_document(str(temp_path))
            finally:
                # Clean up
                if temp_path.exists():
                    temp_path.unlink()
    
    def _get_index_size(self) -> float:
        """Get the size of the index in MB."""
        # This is a placeholder - actual implementation would
        # measure the actual index size on disk
        # For now, estimate based on number of documents
        num_docs = self.pipeline.get_index_size()
        # Rough estimate: 1 KB per document
        return num_docs * 1024 / 1024 / 1024  # Convert to MB
    
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
    
    def generate_scaling_report(self, results: Dict[str, Any]) -> str:
        """Generate a human-readable scaling report."""
        report = []
        report.append("=" * 80)
        report.append("SCALABILITY TEST REPORT")
        report.append("=" * 80)
        report.append(f"\nTimestamp: {results['timestamp']}")
        report.append(f"Test query: {results.get('test_query', 'N/A')}")
        
        report.append("\n" + "=" * 80)
        report.append("CORPUS SCALING RESULTS")
        report.append("=" * 80)
        
        for metrics in results['metrics']:
            report.append(f"\nCorpus size: {metrics['num_documents']} documents")
            report.append(f"  Ingestion time: {metrics['ingestion_time_ms']:.2f} ms")
            report.append(f"  Query latency (mean): {metrics['query_latency_ms']['mean']:.2f} ms")
            report.append(f"  Query latency (P95): {metrics['query_latency_ms']['p95']:.2f} ms")
            report.append(f"  Memory usage: {metrics['memory_mb']:.2f} MB")
            report.append(f"  Index size: {metrics['index_size_mb']:.2f} MB")
        
        report.append("\n" + "=" * 80)
        
        return "\n".join(report)


def main():
    """Run scalability tests from command line."""
    import argparse
    
    parser = argparse.ArgumentParser(description="RAG Pipeline Scalability Tester")
    parser.add_argument('--output', type=str, default='scalability_results',
                       help='Output directory for results')
    parser.add_argument('--corpus-sizes', type=int, nargs='+',
                       default=[10, 50, 100, 500],
                       help='Corpus sizes to test')
    parser.add_argument('--concurrent', type=int, default=10,
                       help='Number of concurrent queries to test')
    
    args = parser.parse_args()
    
    tester = ScalabilityTester(output_dir=args.output)
    
    print("=" * 80)
    print("RAG PIPELINE SCALABILITY TESTS")
    print("=" * 80)
    
    # Test corpus scaling
    print("\n1. Testing corpus scaling...")
    scaling_results = tester.test_corpus_scaling(args.corpus_sizes)
    
    # Test concurrent queries
    print("\n2. Testing concurrent queries...")
    concurrency_results = tester.test_concurrent_queries(args.concurrent)
    
    # Test memory scaling
    print("\n3. Testing memory scaling...")
    memory_results = tester.test_memory_scaling(args.corpus_sizes)
    
    # Generate report
    report = tester.generate_scaling_report(scaling_results)
    print("\n" + report)
    
    # Save report
    report_file = Path(args.output) / f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\nReport saved to: {report_file}")


if __name__ == "__main__":
    main()
