#!/usr/bin/env python3
"""Index knowledge base and retrieval bundles into vector store.

Usage:
    python scripts/run_indexing.py [--reset] [--show-progress]
    
Options:
    --reset         Delete existing collection before indexing
    --show-progress Show progress bar during embedding
    --chunk-size N  Chunk size in characters (default: 500)
    --overlap N     Chunk overlap in characters (default: 100)
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval import Retriever, KNOWLEDGE_DIR, RETRIEVAL_DIR


def main():
    parser = argparse.ArgumentParser(
        description="Index knowledge base into vector store"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete existing collection before indexing",
    )
    parser.add_argument(
        "--show-progress",
        action="store_true",
        help="Show progress bar during embedding",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Chunk size in characters (default: 500)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=100,
        help="Chunk overlap in characters (default: 100)",
    )
    parser.add_argument(
        "--knowledge-dir",
        type=Path,
        default=KNOWLEDGE_DIR,
        help="Path to knowledge directory",
    )
    parser.add_argument(
        "--retrieval-dir",
        type=Path,
        default=RETRIEVAL_DIR,
        help="Path to retrieval bundles directory",
    )
    
    args = parser.parse_args()
    
    # Initialize retriever
    print("Initializing retriever...")
    retriever = Retriever()
    
    # Reset if requested
    if args.reset:
        print("Resetting vector store...")
        retriever.reset()
    
    # Index knowledge base
    print(f"\nIndexing knowledge base...")
    print(f"  Knowledge dir: {args.knowledge_dir}")
    print(f"  Retrieval dir: {args.retrieval_dir}")
    print(f"  Chunk size: {args.chunk_size}")
    print(f"  Overlap: {args.overlap}")
    
    result = retriever.index_knowledge_base(
        knowledge_dir=args.knowledge_dir,
        retrieval_dir=args.retrieval_dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap,
        show_progress=args.show_progress,
    )
    
    # Print results
    print("\n" + "=" * 50)
    print("INDEXING COMPLETE")
    print("=" * 50)
    
    if result.get("knowledge"):
        k = result["knowledge"]
        print(f"\nKnowledge docs:")
        print(f"  Files processed: {k.get('files_processed', 0)}")
        print(f"  Chunks indexed: {k.get('chunks_indexed', 0)}")
    
    if result.get("retrieval"):
        r = result["retrieval"]
        print(f"\nRetrieval bundles:")
        print(f"  Files processed: {r.get('files_processed', 0)}")
        print(f"  Chunks indexed: {r.get('chunks_indexed', 0)}")
    
    print(f"\nTotal:")
    print(f"  Files: {result.get('total_files', 0)}")
    print(f"  Chunks: {result.get('total_chunks', 0)}")
    
    # Show stats
    stats = retriever.get_stats()
    print(f"\nVector store stats:")
    print(f"  Collection: {stats['vector_store']['collection_name']}")
    print(f"  Total vectors: {stats['vector_store']['count']}")
    print(f"  Persist dir: {stats['vector_store']['persist_dir']}")
    
    if stats.get("sources"):
        print(f"\nIndexed sources ({len(stats['sources'])}):")
        for source in stats["sources"][:10]:
            print(f"  - {Path(source).name}")
        if len(stats["sources"]) > 10:
            print(f"  ... and {len(stats['sources']) - 10} more")


if __name__ == "__main__":
    main()
