#!/usr/bin/env python3
"""Test HybridRAG effectiveness.

Compares:
1. VectorRAG only (no graph)
2. HybridRAG (Vector + Graph context)

Metrics:
- Number of relevant documents retrieved
- Coverage of related services
- Context completeness
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.retrieval.retriever import HybridRetriever
from src.graph.retriever import GraphRetriever


def test_queries():
    """Test queries with expected related services."""
    return [
        {
            "query": "checkout service timeout error",
            "expected_services": ["checkout", "cart", "payment", "kafka"],
            "description": "Checkout timeout - should find cart, payment, kafka"
        },
        {
            "query": "cart cannot save items",
            "expected_services": ["cart", "valkey", "redis"],
            "description": "Cart issue - should find redis/valkey"
        },
        {
            "query": "kafka messages not processing",
            "expected_services": ["kafka", "accounting", "fraud"],
            "description": "Kafka issue - should find consumers"
        },
    ]


def run_test():
    print("=" * 60)
    print("HYBRIDRAG EFFECTIVENESS TEST")
    print("=" * 60)
    print()
    
    # Initialize
    print("Loading models...")
    vector_retriever = HybridRetriever(use_reranker=False)  # Faster
    graph_retriever = GraphRetriever(k_hop=2)
    
    queries = test_queries()
    
    results = {
        "vector_only": {"hits": 0, "total": 0},
        "hybrid": {"hits": 0, "total": 0},
    }
    
    for test in queries:
        query = test["query"]
        expected = test["expected_services"]
        
        print("-" * 60)
        print(f"Query: {query}")
        print(f"Expected services: {expected}")
        print()
        
        # ========== VectorRAG Only ==========
        vector_results = vector_retriever.search(query, top_k=5)
        
        vector_services = set()
        for r in vector_results.results:
            source = r.source if hasattr(r, 'source') else r.metadata.get('source_file', '')
            text = r.text.lower()
            for svc in expected:
                if svc.lower() in source.lower() or svc.lower() in text:
                    vector_services.add(svc)
        
        vector_hits = len(vector_services)
        
        # ========== HybridRAG (Vector + Graph) ==========
        # Get graph context
        graph_context = graph_retriever.get_context_for_incident(query, k=2)
        related_services = graph_context.get_all_services()
        
        # Search for related services too
        hybrid_services = vector_services.copy()
        
        if related_services:
            related_query = " ".join(related_services[:5])
            graph_results = vector_retriever.search(related_query, top_k=5)
            
            for r in graph_results.results:
                source = r.source if hasattr(r, 'source') else r.metadata.get('source_file', '')
                text = r.text.lower()
                for svc in expected:
                    if svc.lower() in source.lower() or svc.lower() in text:
                        hybrid_services.add(svc)
        
        hybrid_hits = len(hybrid_services)
        
        # Print results
        print(f"VectorRAG only:")
        print(f"  Found: {vector_services} ({vector_hits}/{len(expected)} services)")
        
        print(f"HybridRAG (Vector + Graph):")
        print(f"  Graph expanded: {related_services[:5]}...")
        print(f"  Found: {hybrid_services} ({hybrid_hits}/{len(expected)} services)")
        
        improvement = hybrid_hits - vector_hits
        if improvement > 0:
            print(f"  ✅ +{improvement} more services found with HybridRAG")
        elif improvement == 0:
            print(f"  = Same coverage")
        else:
            print(f"  ⚠️ {improvement} fewer (edge case)")
        
        results["vector_only"]["hits"] += vector_hits
        results["vector_only"]["total"] += len(expected)
        results["hybrid"]["hits"] += hybrid_hits
        results["hybrid"]["total"] += len(expected)
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    vector_recall = results["vector_only"]["hits"] / results["vector_only"]["total"] * 100
    hybrid_recall = results["hybrid"]["hits"] / results["hybrid"]["total"] * 100
    
    print(f"VectorRAG Only:  {results['vector_only']['hits']}/{results['vector_only']['total']} = {vector_recall:.1f}% recall")
    print(f"HybridRAG:       {results['hybrid']['hits']}/{results['hybrid']['total']} = {hybrid_recall:.1f}% recall")
    print()
    
    if hybrid_recall > vector_recall:
        print(f"✅ HybridRAG improves recall by +{hybrid_recall - vector_recall:.1f}%")
    else:
        print(f"= No improvement (may need more graph edges)")


if __name__ == "__main__":
    run_test()

