#!/usr/bin/env python3
"""
Experiment execution script that generates REAL results.

This script will:
1. Load actual documents (if provided)
2. Execute experiments with real data
3. Generate actual result files with timestamps
4. Calculate metrics from raw observations

IMPORTANT: This script will FAIL if documents are not provided.
It will NOT generate fake results.
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import config
from src.pipeline import RAGPipeline


class ExperimentExecutor:
    """Executes experiments and generates REAL results."""
    
    def __init__(self):
        self.pipeline = RAGPipeline()
        self.results_dir = Path("experiments/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met."""
        print("=" * 80)
        print("CHECKING PREREQUISITES")
        print("=" * 80)
        
        # Check documents
        docs_dir = Path("data/documents")
        if not docs_dir.exists():
            print("❌ FAIL: data/documents/ directory does not exist")
            print("   Create it and add financial documents (PDFs)")
            return False
        
        pdf_files = list(docs_dir.glob("*.pdf"))
        if len(pdf_files) == 0:
            print("❌ FAIL: No PDF documents found in data/documents/")
            print("   Download financial documents from SEC EDGAR")
            return False
        
        print(f"✅ Found {len(pdf_files)} documents")
        
        # Check benchmark
        benchmark_file = Path("benchmarks/comprehensive_benchmark.json")
        if not benchmark_file.exists():
            print("❌ FAIL: Benchmark file not found")
            return False
        
        with open(benchmark_file) as f:
            benchmark = json.load(f)
        
        num_questions = len(benchmark.get("questions", []))
        print(f"✅ Found {num_questions} benchmark questions")
        
        # Check API key
        if not config.openai_api_key:
            print("❌ FAIL: OPENAI_API_KEY not set")
            print("   Set it in .env file")
            return False
        
        print("✅ OPENAI_API_KEY is set")
        
        print("\n✅ All prerequisites met")
        return True
    
    def ingest_documents(self) -> Dict[str, Any]:
        """Ingest all documents and return metadata."""
        print("\n" + "=" * 80)
        print("INGESTING DOCUMENTS")
        print("=" * 80)
        
        docs_dir = Path("data/documents")
        pdf_files = list(docs_dir.glob("*.pdf"))
        
        ingestion_results = []
        total_start = time.time()
        
        for pdf_file in pdf_files:
            print(f"\nIngesting: {pdf_file.name}")
            start = time.time()
            
            try:
                result = self.pipeline.ingest_document(str(pdf_file))
                elapsed = (time.time() - start) * 1000
                
                ingestion_results.append({
                    "filename": pdf_file.name,
                    "status": "success",
                    "chunks_created": result.get("num_chunks", 0),
                    "ingestion_time_ms": elapsed
                })
                
                print(f"  ✅ Success: {result.get('num_chunks', 0)} chunks in {elapsed:.2f}ms")
                
            except Exception as e:
                ingestion_results.append({
                    "filename": pdf_file.name,
                    "status": "failed",
                    "error": str(e)
                })
                print(f"  ❌ Failed: {e}")
        
        total_elapsed = (time.time() - total_start) * 1000
        
        return {
            "total_documents": len(pdf_files),
            "successful": sum(1 for r in ingestion_results if r["status"] == "success"),
            "failed": sum(1 for r in ingestion_results if r["status"] == "failed"),
            "total_time_ms": total_elapsed,
            "results": ingestion_results
        }
    
    def run_experiment(self, experiment_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single experiment and return REAL results."""
        print(f"\n{'=' * 80}")
        print(f"RUNNING EXPERIMENT: {experiment_id}")
        print(f"{'=' * 80}")
        
        # Load benchmark
        with open("benchmarks/comprehensive_benchmark.json") as f:
            benchmark = json.load(f)
        
        questions = benchmark.get("questions", [])
        
        # Initialize result structure
        result = {
            "experiment_id": experiment_id,
            "timestamp": datetime.utcnow().isoformat(),
            "configuration": config_data,
            "dataset": {
                "benchmark_file": "benchmarks/comprehensive_benchmark.json",
                "total_questions": len(questions)
            },
            "raw_results": {
                "per_query_results": []
            },
            "metrics": {
                "retrieval": {},
                "generation": {},
                "citation": {},
                "performance": {},
                "cost": {}
            }
        }
        
        # Execute queries
        print(f"\nExecuting {len(questions)} queries...")
        all_latencies = []
        
        for i, question in enumerate(questions, 1):
            query_text = question.get("question", "")
            print(f"\n  [{i}/{len(questions)}] {query_text[:60]}...")
            
            start = time.time()
            
            try:
                # Execute query
                response = self.pipeline.query(query_text)
                latency = (time.time() - start) * 1000
                all_latencies.append(latency)
                
                # Record raw result
                raw_result = {
                    "query_id": question.get("question_id"),
                    "query_text": query_text,
                    "expected_answer": question.get("expected_answer"),
                    "generated_answer": response.answer if response else None,
                    "confidence": response.confidence if response else None,
                    "citations": [
                        {
                            "document": c.document,
                            "page": c.page,
                            "excerpt": c.excerpt
                        }
                        for c in (response.citations if response else [])
                    ],
                    "latency_ms": latency,
                    "status": "success"
                }
                
                result["raw_results"]["per_query_results"].append(raw_result)
                
                print(f"    ✅ Success: {latency:.2f}ms")
                
            except Exception as e:
                raw_result = {
                    "query_id": question.get("question_id"),
                    "query_text": query_text,
                    "status": "failed",
                    "error": str(e)
                }
                result["raw_results"]["per_query_results"].append(raw_result)
                print(f"    ❌ Failed: {e}")
        
        # Calculate metrics from raw results
        successful_queries = [r for r in result["raw_results"]["per_query_results"] if r["status"] == "success"]
        
        if all_latencies:
            all_latencies.sort()
            result["metrics"]["performance"] = {
                "latency_p50_ms": all_latencies[len(all_latencies) // 2],
                "latency_p95_ms": all_latencies[int(len(all_latencies) * 0.95)],
                "latency_p99_ms": all_latencies[int(len(all_latencies) * 0.99)],
                "throughput_qps": len(successful_queries) / (sum(all_latencies) / 1000)
            }
        
        result["metrics"]["retrieval"] = {
            "total_queries": len(questions),
            "successful_queries": len(successful_queries),
            "failed_queries": len(questions) - len(successful_queries)
        }
        
        # Save result
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        result_file = self.results_dir / f"{experiment_id}-{timestamp}.json"
        
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        
        print(f"\n✅ Results saved to: {result_file}")
        
        return result
    
    def run_all_experiments(self):
        """Run all experiments from manifest."""
        print("\n" + "=" * 80)
        print("RAG PIPELINE - EXPERIMENT EXECUTION")
        print("=" * 80)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Cannot proceed: Prerequisites not met")
            sys.exit(1)
        
        # Ingest documents
        ingestion_result = self.ingest_documents()
        
        # Load manifest
        with open("experiments/manifest.json") as f:
            manifest = json.load(f)
        
        # Run experiments
        results = []
        for exp in manifest["experiments"]:
            exp_id = exp["id"]
            exp_config = exp.get("configuration", {})
            
            result = self.run_experiment(exp_id, exp_config)
            results.append(result)
        
        # Summary
        print("\n" + "=" * 80)
        print("EXPERIMENT SUMMARY")
        print("=" * 80)
        print(f"Total experiments: {len(results)}")
        print(f"Results saved to: {self.results_dir}")
        
        for result in results:
            exp_id = result["experiment_id"]
            num_queries = len(result["raw_results"]["per_query_results"])
            print(f"  {exp_id}: {num_queries} queries executed")


def main():
    """Main entry point."""
    executor = ExperimentExecutor()
    executor.run_all_experiments()


if __name__ == "__main__":
    main()
