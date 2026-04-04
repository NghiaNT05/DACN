#!/usr/bin/env python3
"""Build and populate the service dependency graph.

Usage:
    python scripts/run_graph_setup.py [--source otel|manual] [--reset]
"""

import sys
import json
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.graph.builder import GraphBuilder, build_otel_demo_graph
from src.graph.store import get_graph_store, JsonGraphStore


def main():
    parser = argparse.ArgumentParser(description="Setup service dependency graph")
    parser.add_argument("--source", choices=["otel", "manual"], default="otel",
                        help="Graph source (default: otel)")
    parser.add_argument("--reset", action="store_true",
                        help="Clear existing graph before import")
    parser.add_argument("--neo4j", action="store_true",
                        help="Use Neo4j instead of JSON store")
    parser.add_argument("--show", action="store_true",
                        help="Show graph structure after setup")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("SERVICE DEPENDENCY GRAPH SETUP")
    print("=" * 60)
    
    # Get graph store
    if args.neo4j:
        print("\nConnecting to Neo4j...")
        try:
            store = get_graph_store(use_neo4j=True)
            print("  Connected to Neo4j")
        except Exception as e:
            print(f"  Failed to connect to Neo4j: {e}")
            print("  Falling back to JSON store")
            store = get_graph_store(use_neo4j=False)
    else:
        print("\nUsing JSON store...")
        store = get_graph_store(use_neo4j=False)
    
    # Reset if requested
    if args.reset:
        print("\nClearing existing graph...")
        store.clear_graph()
    
    # Build graph
    print(f"\nBuilding graph from: {args.source}")
    
    if args.source == "otel":
        graph = build_otel_demo_graph()
    else:
        # Manual graph - could be extended
        builder = GraphBuilder()
        graph = builder.get_graph()
    
    # Import graph
    print(f"\nImporting graph...")
    stats = store.import_graph(graph)
    print(f"  Nodes imported: {stats['nodes_added']}")
    print(f"  Edges imported: {stats['edges_added']}")
    
    # Show stats
    print("\n" + "-" * 60)
    print("GRAPH STATISTICS")
    print("-" * 60)
    
    graph_stats = store.get_stats()
    print(f"  Total nodes: {graph_stats.get('node_count', len(graph.nodes))}")
    print(f"  Total edges: {graph_stats.get('edge_count', len(graph.edges))}")
    
    if args.show:
        print("\n" + "-" * 60)
        print("GRAPH STRUCTURE")
        print("-" * 60)
        
        # Show nodes by type
        print("\nServices by type:")
        type_counts = {}
        for node in graph.nodes:
            t = node.service_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        for t, count in sorted(type_counts.items()):
            print(f"  {t}: {count}")
        
        # Show some edges
        print("\nSample dependencies:")
        for edge in graph.edges[:10]:
            print(f"  {edge.source_id} --[{edge.dependency_type.value}]--> {edge.target_id}")
        
        if len(graph.edges) > 10:
            print(f"  ... and {len(graph.edges) - 10} more")
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE")
    print("=" * 60)
    
    # Show file location for JSON store
    if isinstance(store, JsonGraphStore):
        print(f"\nGraph saved to: {store.file_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
