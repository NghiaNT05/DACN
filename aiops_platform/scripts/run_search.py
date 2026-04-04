#!/usr/bin/env python3
"""Search the knowledge base using semantic search.

Usage:
    python scripts/run_search.py --query "OOM killed container"
    python scripts/run_search.py --query "startup probe failed" --top-k 5
    
Options:
    --query, -q     Search query (required)
    --top-k, -k     Number of results (default: 5)
    --threshold     Minimum score threshold (default: 0.3)
    --json          Output as JSON
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import Retriever


def main():
    parser = argparse.ArgumentParser(
        description="Search knowledge base using semantic search"
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        required=True,
        help="Search query",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Number of results to return (default: 5)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.3,
        help="Minimum score threshold (default: 0.3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--filter-source",
        type=str,
        help="Filter by source file pattern",
    )
    parser.add_argument(
        "--context",
        action="store_true",
        help="Show concatenated context from results",
    )
    
    args = parser.parse_args()
    
    # Initialize retriever
    retriever = Retriever()
    
    # Check if index exists
    stats = retriever.get_stats()
    if stats["vector_store"]["count"] == 0:
        print("ERROR: Vector store is empty. Run indexing first:")
        print("  python scripts/run_indexing.py")
        sys.exit(1)
    
    # Search
    result = retriever.search(
        query=args.query,
        top_k=args.top_k,
        score_threshold=args.threshold,
        filter_source=args.filter_source,
    )
    
    # Output
    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
        return
    
    print("=" * 60)
    print(f"SEARCH RESULTS")
    print(f"Query: {args.query}")
    print(f"Found: {result.total_found} results")
    print("=" * 60)
    
    if not result.results:
        print("\nNo results found. Try:")
        print("  - Lowering the threshold (--threshold 0.1)")
        print("  - Using different keywords")
        return
    
    for i, r in enumerate(result.results, 1):
        source_name = Path(r.metadata.get("source_file", "unknown")).name
        print(f"\n[{i}] Score: {r.score:.3f} | Source: {source_name}")
        print("-" * 40)
        # Show truncated text
        text = r.text[:300] + "..." if len(r.text) > 300 else r.text
        print(text)
    
    if args.context:
        print("\n" + "=" * 60)
        print("COMBINED CONTEXT")
        print("=" * 60)
        print(result.get_context(max_chunks=3))


if __name__ == "__main__":
    main()
