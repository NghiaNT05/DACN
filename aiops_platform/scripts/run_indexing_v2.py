#!/usr/bin/env python3
"""Advanced indexing script with hybrid search support.

Usage:
    python scripts/run_indexing_v2.py [--reset] [--show-progress]
"""

import sys
import time
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.retriever import HybridRetriever
from src.retrieval.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP


def main():
    parser = argparse.ArgumentParser(description="Index knowledge base with hybrid search")
    parser.add_argument("--reset", action="store_true", help="Reset existing indexes")
    parser.add_argument("--show-progress", action="store_true", help="Show progress")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE,
                        help=f"Chunk size (default: {DEFAULT_CHUNK_SIZE})")
    parser.add_argument("--overlap", type=int, default=DEFAULT_CHUNK_OVERLAP,
                        help=f"Chunk overlap (default: {DEFAULT_CHUNK_OVERLAP})")
    parser.add_argument("--no-reranker", action="store_true", 
                        help="Skip loading reranker model")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("HYBRID KNOWLEDGE BASE INDEXING (v2)")
    print("=" * 60)
    print(f"Chunk size: {args.chunk_size}")
    print(f"Overlap: {args.overlap}")
    print(f"Reranker: {'disabled' if args.no_reranker else 'enabled'}")
    print()
    
    # Initialize retriever
    print("Initializing hybrid retriever...")
    start_time = time.time()
    
    retriever = HybridRetriever(use_reranker=not args.no_reranker)
    init_time = time.time() - start_time
    print(f"  Initialization time: {init_time:.1f}s")
    
    # Reset if requested
    if args.reset:
        print("\nResetting existing indexes...")
        retriever.reset()
    
    # Index knowledge base
    print("\nIndexing knowledge base...")
    start_time = time.time()
    
    stats = retriever.index_knowledge_base(
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        show_progress=args.show_progress,
    )
    
    index_time = time.time() - start_time
    
    # Print results
    print("\n" + "=" * 60)
    print("INDEXING COMPLETE")
    print("=" * 60)
    print(f"Status: {stats.get('status', 'unknown')}")
    print(f"Files processed: {stats.get('files_processed', 0)}")
    print(f"Vector chunks indexed: {stats.get('chunks_indexed', 0)}")
    print(f"BM25 documents indexed: {stats.get('bm25_indexed', 0)}")
    print(f"Total time: {index_time:.1f}s")
    
    # Print detailed stats
    print("\n" + "-" * 60)
    print("INDEX STATISTICS")
    print("-" * 60)
    full_stats = retriever.get_stats()
    
    vector_stats = full_stats.get('vector_store', {})
    print(f"Vector store collection: {vector_stats.get('collection_name', 'N/A')}")
    print(f"Vector store count: {vector_stats.get('count', 'N/A')}")
    
    bm25_stats = full_stats.get('bm25_index', {})
    print(f"BM25 corpus size: {bm25_stats.get('corpus_size', 'N/A')}")
    print(f"BM25 vocabulary size: {bm25_stats.get('vocabulary_size', 'N/A')}")
    
    weights = full_stats.get('weights', {})
    print(f"Hybrid weights: vector={weights.get('vector', 'N/A'):.2f}, bm25={weights.get('bm25', 'N/A'):.2f}")
    print(f"Reranker enabled: {full_stats.get('has_reranker', False)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
