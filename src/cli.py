"""
src/cli.py — Research-Grade Interactive Terminal CLI & Operator Console.

Provides an interactive REPL with live querying, citation tracing,
Self-RAG critique token inspection, CRAG action monitoring, semantic cache telemetry,
and real-time document ingestion.
"""

import sys
import os
import time
import argparse
from typing import Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.pipeline import RAGPipeline
from src.core.models import QueryResponse


class TerminalColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'
    DIM = '\033[2m'


BANNER = f"""{TerminalColors.CYAN}{TerminalColors.BOLD}
================================================================================
   ____             _    ____ _ _            _            ____      _    ____ 
  |  _ \           / \  / ___(_) |_ __ _  __| | ___ _ __ |  _ \    / \  / ___|
  | |_) |_____    / _ \| |  _| | __/ _` |/ _` |/ _ \ '__|| |_) |  / _ \| |  _ 
  |  _ <|_____|  / ___ \ |_| | | || (_| | (_| |  __/ |   |  _ <  / ___ \ |_| |
  |_| \_\       /_/   \_\____|_|\__\__,_|\__,_|\___|_|   |_| \_\/_/   \_\____|
                                                                                
  Enterprise-Grade Adaptive RAG Pipeline Architecture & Evaluation Engine
  Stanford CS / Anthropic / Google Research Standard
================================================================================{TerminalColors.RESET}
{TerminalColors.GREEN}Active SOTA Capabilities:{TerminalColors.RESET}
  * Anthropic Contextual Retrieval (Chunk-level situated document grounding)
  * Stanford DSPy / IR-CoT Dynamic Query Decomposition
  * Gao et al. ACL 2023 HyDE (Hypothetical Document Embeddings)
  * Corrective RAG (CRAG) & Self-RAG Reflection Critique ([ISREL], [ISSUP], [ISUSE])
  * Sub-5ms Cosine Similarity Semantic Cache
  * Programmatic Numerical Reasoning Engine (Deterministic arithmetic & comparisons)
"""


def format_response_card(resp: QueryResponse, total_ms: float) -> str:
    """Format query response into an engineering inspection card."""
    lines = []
    lines.append(f"\n{TerminalColors.BOLD}{TerminalColors.GREEN}=== ANSWER ==={TerminalColors.RESET}")
    lines.append(f"{resp.answer}\n")

    # Evidence & Confidence
    sup_color = TerminalColors.GREEN if resp.support_level == "supported" or resp.support_level == "fully_supported" else TerminalColors.YELLOW
    lines.append(f"{TerminalColors.BOLD}Verification Status:{TerminalColors.RESET} {sup_color}{resp.support_level.upper()}{TerminalColors.RESET} | {TerminalColors.BOLD}Confidence:{TerminalColors.RESET} {resp.confidence:.2f}")

    # Citations
    if resp.citations:
        lines.append(f"\n{TerminalColors.BOLD}{TerminalColors.BLUE}=== CITATIONS ({len(resp.citations)}) ==={TerminalColors.RESET}")
        for i, cite in enumerate(resp.citations, 1):
            lines.append(f"  {TerminalColors.DIM}[{i}]{TerminalColors.RESET} {cite}")

    # Telemetry & SOTA Modules
    lines.append(f"\n{TerminalColors.BOLD}{TerminalColors.CYAN}=== PIPELINE TELEMETRY ==={TerminalColors.RESET}")
    q_type = resp.retrieval_metadata.get("query_type", "unknown")
    crag_act = resp.retrieval_metadata.get("crag_action", "N/A")
    lines.append(f"  * Query Classification: {TerminalColors.BOLD}{q_type}{TerminalColors.RESET}")
    lines.append(f"  * CRAG Action:          {TerminalColors.BOLD}{crag_act.upper()}{TerminalColors.RESET}")

    # Self-RAG
    self_rag = resp.retrieval_metadata.get("self_rag_critique", {})
    if self_rag:
        is_rel = f"{TerminalColors.GREEN}PASS{TerminalColors.RESET}" if self_rag.get("is_relevant") else f"{TerminalColors.RED}FAIL{TerminalColors.RESET}"
        is_sup = f"{TerminalColors.GREEN}PASS{TerminalColors.RESET}" if self_rag.get("is_supported") else f"{TerminalColors.RED}FAIL{TerminalColors.RESET}"
        util = self_rag.get("utility_score", 0.0)
        lines.append(f"  * Self-RAG Critique:    [ISREL]: {is_rel} | [ISSUP]: {is_sup} | [ISUSE]: {util:.2f}")

    # Faithfulness / FActScore
    faith_report = resp.retrieval_metadata.get("faithfulness_report", {})
    if faith_report:
        faith_score = faith_report.get("claim_level_faithfulness", 1.0)
        halluc_rate = faith_report.get("hallucination_rate", 0.0)
        lines.append(f"  * Claim Faithfulness:   {faith_score:.1%} | Hallucination Rate: {halluc_rate:.1%}")

    # Numerical reasoning
    num_res = resp.retrieval_metadata.get("numerical_reasoning", {})
    if num_res:
        lines.append(f"  * Numerical Reasoner:   {num_res.get('operation')} -> {num_res.get('result')} {num_res.get('unit', '')} ({num_res.get('reasoning')})")

    # Latencies
    ret_lat = resp.latency.get("retrieval_ms", 0.0)
    gen_lat = resp.latency.get("generation_ms", 0.0)
    lines.append(f"  * Latency:              Retrieval: {ret_lat:.1f}ms | Generation: {gen_lat:.1f}ms | Total Turn: {total_ms:.1f}ms")

    return "\n".join(lines)


def run_interactive_repl(pipeline: RAGPipeline):
    """Run interactive terminal REPL."""
    print(BANNER)
    print(f"{TerminalColors.BOLD}Commands:{TerminalColors.RESET}")
    print("  /ingest <path>    - Ingest a text, markdown, or PDF document")
    print("  /cache            - Display semantic cache performance metrics")
    print("  /cache-clear      - Flush semantic cache entries")
    print("  /stats            - Show index corpus metrics")
    print("  /help             - Show this help message")
    print("  /exit, /quit      - Terminate console session\n")

    while True:
        try:
            user_input = input(f"{TerminalColors.BOLD}{TerminalColors.CYAN}rag-pipeline> {TerminalColors.RESET}").strip()
            if not user_input:
                continue

            if user_input in ("/exit", "/quit", "exit", "quit"):
                print(f"\n{TerminalColors.YELLOW}Exiting RAG console. Goodbye!{TerminalColors.RESET}")
                break

            elif user_input in ("/help", "help"):
                print("Available commands: /ingest <path>, /cache, /cache-clear, /stats, /help, /exit")
                continue

            elif user_input == "/cache":
                stats = pipeline.semantic_cache.stats()
                print(f"\n{TerminalColors.BOLD}=== SEMANTIC CACHE TELEMETRY ==={TerminalColors.RESET}")
                for k, v in stats.items():
                    print(f"  {k:20}: {v}")
                print()
                continue

            elif user_input == "/cache-clear":
                pipeline.semantic_cache.clear()
                print(f"{TerminalColors.GREEN}Semantic cache cleared.{TerminalColors.RESET}")
                continue

            elif user_input == "/stats":
                v_count = pipeline.retriever.vector_index.count()
                b_count = pipeline.retriever.bm25_index.count()
                print(f"\n{TerminalColors.BOLD}=== CORPUS INDEX STATS ==={TerminalColors.RESET}")
                print(f"  Vector Index Chunks: {v_count}")
                print(f"  BM25 Index Chunks:   {b_count}")
                print(f"  Total Queries Served:{pipeline.query_count}\n")
                continue

            elif user_input.startswith("/ingest "):
                filepath = user_input[8:].strip()
                if not os.path.exists(filepath):
                    print(f"{TerminalColors.RED}Error: File '{filepath}' does not exist.{TerminalColors.RESET}")
                    continue
                print(f"Ingesting {filepath}...")
                t0 = time.perf_counter()
                meta = pipeline.ingest_document(filepath)
                dt = (time.perf_counter() - t0) * 1000
                chunks_count = meta.get("num_chunks", "N/A")
                print(f"{TerminalColors.GREEN}Successfully ingested {chunks_count} chunks in {dt:.1f}ms.{TerminalColors.RESET}")
                continue

            # Standard Query
            t_start = time.perf_counter()
            resp = pipeline.query(user_input, use_cache=True, use_hyde=False)
            t_elapsed = (time.perf_counter() - t_start) * 1000

            card = format_response_card(resp, t_elapsed)
            print(card)
            print("-" * 80)

        except KeyboardInterrupt:
            print(f"\n{TerminalColors.YELLOW}Operation cancelled by user.{TerminalColors.RESET}")
            break
        except Exception as e:
            print(f"\n{TerminalColors.RED}Error processing command: {e}{TerminalColors.RESET}")


def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline Terminal Operator CLI")
    parser.add_argument("--query", "-q", type=str, help="Execute single query and exit")
    parser.add_argument("--ingest", "-i", type=str, help="Ingest document before running")
    parser.add_argument("--hyde", action="store_true", help="Enable HyDE zero-shot dense query synthesis")
    args = parser.parse_args()

    pipeline = RAGPipeline()

    if args.ingest:
        if os.path.exists(args.ingest):
            meta = pipeline.ingest_document(args.ingest)
            print(f"Ingested {args.ingest} into pipeline corpus: {meta.get('num_chunks', 0)} chunks.")
        else:
            print(f"File not found: {args.ingest}", file=sys.stderr)
            sys.exit(1)

    if args.query:
        t0 = time.perf_counter()
        resp = pipeline.query(args.query, use_cache=True, use_hyde=args.hyde)
        total_ms = (time.perf_counter() - t0) * 1000
        print(format_response_card(resp, total_ms))
    else:
        run_interactive_repl(pipeline)


if __name__ == "__main__":
    main()
