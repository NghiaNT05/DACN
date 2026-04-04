#!/usr/bin/env python3
"""GraphRAG search - combines vector search with service graph context.

Usage:
    python scripts/run_graphrag_search.py --query "checkout service timeout"
    python scripts/run_graphrag_search.py --query "kafka connection error" --k-hop 2
    python scripts/run_graphrag_search.py --services checkout cart payment
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def main():
    parser = argparse.ArgumentParser(description="GraphRAG search for incidents")
    parser.add_argument("--query", "-q", help="Search query (incident description)")
    parser.add_argument("--services", "-s", nargs="+", help="Service IDs to search for")
    parser.add_argument("--top-k", "-k", type=int, default=5, help="Number of results")
    parser.add_argument("--k-hop", type=int, default=2, help="Graph expansion hops")
    parser.add_argument("--no-graph", action="store_true", help="Disable graph context")
    parser.add_argument("--no-reranker", action="store_true", help="Disable reranker")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    args = parser.parse_args()
    
    if not args.query and not args.services:
        parser.error("Either --query or --services is required")
    
    # Import here for cleaner startup
    from src.graph.fusion import create_graph_rag
    from src.graph.builder import build_otel_demo_graph
    from src.graph.store import JsonGraphStore
    
    print("=" * 70)
    print("GRAPHRAG SEARCH")
    print("=" * 70)
    
    # Ensure graph is set up
    print("\nInitializing...")
    store = JsonGraphStore()
    if store.get_stats().get("total_nodes", 0) == 0:
        print("  Setting up service graph (first run)...")
        graph = build_otel_demo_graph()
        store.import_graph(graph)
        print(f"  Imported {len(graph.nodes)} services, {len(graph.edges)} dependencies")
    
    # Create GraphRAG
    print("  Loading models...")
    graph_rag = create_graph_rag(
        use_reranker=not args.no_reranker,
        k_hop=args.k_hop,
    )
    
    # Re-index vector store if needed
    print("  Checking vector index...")
    stats = graph_rag.vector_retriever.get_stats()
    if stats.get('vector_store', {}).get('count', 0) == 0:
        print("  Indexing knowledge base...")
        graph_rag.vector_retriever.index_knowledge_base()
    
    # Perform search
    print("\n" + "-" * 70)
    
    if args.services:
        query_text = " ".join(args.services) + " incident"
        print(f"Searching for services: {', '.join(args.services)}")
        results = graph_rag.search_for_services(
            args.services,
            top_k=args.top_k,
            k_hop=args.k_hop,
        )
    else:
        print(f"Query: {args.query}")
        results = graph_rag.search(
            args.query,
            top_k=args.top_k,
            k_hop=args.k_hop,
            use_graph=not args.no_graph,
        )
    
    print("-" * 70)
    
    # Output results
    if args.json:
        print(json.dumps(results.to_dict(), indent=2))
        return 0
    
    # Show graph context
    ctx = results.graph_context
    if ctx.incident_services:
        print(f"\nServices detected: {', '.join(ctx.incident_services)}")
        if ctx.related_services:
            print(f"Related services ({args.k_hop}-hop): {', '.join(ctx.related_services[:10])}")
            if len(ctx.related_services) > 10:
                print(f"  ... and {len(ctx.related_services) - 10} more")
    
    # Show results
    print(f"\n{'='*70}")
    print(f"RESULTS ({len(results.results)} found)")
    print(f"{'='*70}\n")
    
    for i, r in enumerate(results.results):
        print(f"[{i+1}] Final Score: {r.final_score:.3f}")
        
        if args.verbose:
            print(f"    Vector: {r.vector_score:.3f} | Graph: {r.graph_score:.3f} | Recency: {r.recency_score:.3f}")
            if r.related_services:
                print(f"    Services: {', '.join(r.related_services)}")
            if r.hop_distance is not None:
                print(f"    Hop distance: {r.hop_distance}")
        
        # Get source filename
        source = r.source.split("/")[-1] if "/" in r.source else r.source
        print(f"    Source: {source}")
        print("-" * 50)
        
        # Show text preview
        text_preview = r.text[:300] + "..." if len(r.text) > 300 else r.text
        print(f"    {text_preview}")
        print()
    
    # Show stats
    if args.verbose:
        print("-" * 70)
        print("SEARCH STATS")
        print("-" * 70)
        for key, value in results.search_stats.items():
            print(f"  {key}: {value}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
