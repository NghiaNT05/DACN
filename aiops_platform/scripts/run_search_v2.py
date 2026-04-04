#!/usr/bin/env python3
"""Advanced search script with hybrid search and reranking.

Usage:
    python scripts/run_search_v2.py --query "OOM killed pod"
    python scripts/run_search_v2.py --query "checkout failing" --no-rerank
    python scripts/run_search_v2.py --query "kafka timeout" --compare
"""

import sys
import time
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.retriever import Retriever, HybridRetriever
from src.retrieval.config import DEFAULT_TOP_K, RERANK_TOP_K


def search_basic(query: str, top_k: int) -> dict:
    """Run basic vector search."""
    retriever = Retriever()
    start = time.time()
    results = retriever.search(query, top_k=top_k)
    elapsed = time.time() - start
    
    return {
        "type": "vector",
        "query": query,
        "time": elapsed,
        "results": [
            {
                "score": r.score,
                "source": r.metadata.get('source_file', 'unknown'),
                "text": r.text[:200] + "..." if len(r.text) > 200 else r.text,
            }
            for r in results.results
        ]
    }


def search_hybrid(query: str, top_k: int, use_rerank: bool) -> dict:
    """Run hybrid search with optional reranking."""
    retriever = HybridRetriever(use_reranker=use_rerank)
    start = time.time()
    results = retriever.search(query, top_k=top_k, use_reranker=use_rerank)
    elapsed = time.time() - start
    
    return {
        "type": results.search_type,
        "query": query,
        "time": elapsed,
        "results": [
            {
                "final_score": r.final_score,
                "vector_score": r.vector_score,
                "bm25_score": r.bm25_score,
                "rerank_score": r.rerank_score,
                "source": r.source,
                "text": r.text[:200] + "..." if len(r.text) > 200 else r.text,
            }
            for r in results.results
        ]
    }


def print_results(results: dict, verbose: bool = False):
    """Pretty print search results."""
    print(f"\n{'='*60}")
    print(f"SEARCH RESULTS ({results['type'].upper()})")
    print(f"Query: {results['query']}")
    print(f"Time: {results['time']:.3f}s")
    print(f"Found: {len(results['results'])} results")
    print(f"{'='*60}\n")
    
    for i, r in enumerate(results['results']):
        print(f"[{i+1}] ", end="")
        
        if 'final_score' in r:
            print(f"Final: {r['final_score']:.3f} | ", end="")
            if verbose:
                print(f"Vec: {r['vector_score']:.3f} | BM25: {r['bm25_score']:.3f}", end="")
                if r['rerank_score'] is not None:
                    print(f" | Rerank: {r['rerank_score']:.3f}", end="")
                print(" | ", end="")
        else:
            print(f"Score: {r['score']:.3f} | ", end="")
        
        # Extract filename from path
        source = r['source']
        if '/' in source:
            source = source.split('/')[-1]
        print(f"Source: {source}")
        
        print("-" * 40)
        print(r['text'])
        print()


def compare_methods(query: str, top_k: int):
    """Compare basic vs hybrid search."""
    print("\n" + "="*70)
    print("COMPARISON: Basic Vector vs Hybrid Search")
    print("="*70)
    
    # Basic search
    print("\n[1/3] Running basic vector search...")
    basic = search_basic(query, top_k)
    
    # Hybrid without rerank
    print("[2/3] Running hybrid search (no rerank)...")
    hybrid_no_rerank = search_hybrid(query, top_k, use_rerank=False)
    
    # Hybrid with rerank
    print("[3/3] Running hybrid search with reranking...")
    hybrid_rerank = search_hybrid(query, top_k, use_rerank=True)
    
    # Compare results
    print("\n" + "-"*70)
    print("RESULTS COMPARISON")
    print("-"*70)
    
    print(f"\n{'Method':<25} {'Time':<10} {'Top Source':<30} {'Score':<10}")
    print("-"*75)
    
    if basic['results']:
        top = basic['results'][0]
        source = top['source'].split('/')[-1] if '/' in top['source'] else top['source']
        print(f"{'Basic Vector':<25} {basic['time']:<10.3f} {source:<30} {top['score']:<10.3f}")
    
    if hybrid_no_rerank['results']:
        top = hybrid_no_rerank['results'][0]
        source = top['source'].split('/')[-1] if '/' in top['source'] else top['source']
        print(f"{'Hybrid (no rerank)':<25} {hybrid_no_rerank['time']:<10.3f} {source:<30} {top['final_score']:<10.3f}")
    
    if hybrid_rerank['results']:
        top = hybrid_rerank['results'][0]
        source = top['source'].split('/')[-1] if '/' in top['source'] else top['source']
        print(f"{'Hybrid + Rerank':<25} {hybrid_rerank['time']:<10.3f} {source:<30} {top['final_score']:<10.3f}")
    
    print()
    
    # Show detailed results
    print("\n" + "="*70)
    print("DETAILED RESULTS")
    print("="*70)
    
    print("\n--- Basic Vector Search ---")
    for i, r in enumerate(basic['results'][:3]):
        source = r['source'].split('/')[-1] if '/' in r['source'] else r['source']
        print(f"  [{i+1}] {r['score']:.3f} | {source}")
    
    print("\n--- Hybrid Search (no rerank) ---")
    for i, r in enumerate(hybrid_no_rerank['results'][:3]):
        source = r['source'].split('/')[-1] if '/' in r['source'] else r['source']
        print(f"  [{i+1}] {r['final_score']:.3f} (v:{r['vector_score']:.3f} b:{r['bm25_score']:.3f}) | {source}")
    
    print("\n--- Hybrid + Rerank ---")
    for i, r in enumerate(hybrid_rerank['results'][:3]):
        source = r['source'].split('/')[-1] if '/' in r['source'] else r['source']
        rerank = f"r:{r['rerank_score']:.3f}" if r['rerank_score'] is not None else "r:N/A"
        print(f"  [{i+1}] {r['final_score']:.3f} ({rerank}) | {source}")


def main():
    parser = argparse.ArgumentParser(description="Advanced hybrid search")
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--top-k", "-k", type=int, default=RERANK_TOP_K,
                        help=f"Number of results (default: {RERANK_TOP_K})")
    parser.add_argument("--no-rerank", action="store_true", 
                        help="Disable cross-encoder reranking")
    parser.add_argument("--basic", action="store_true",
                        help="Use basic vector search only")
    parser.add_argument("--compare", action="store_true",
                        help="Compare all search methods")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed scores")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    
    args = parser.parse_args()
    
    if args.compare:
        compare_methods(args.query, args.top_k)
        return 0
    
    if args.basic:
        results = search_basic(args.query, args.top_k)
    else:
        results = search_hybrid(args.query, args.top_k, use_rerank=not args.no_rerank)
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results, verbose=args.verbose)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
