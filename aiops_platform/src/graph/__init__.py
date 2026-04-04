"""Graph module for HybridRAG.

Based on: "HybridRAG: Integrating Knowledge Graphs and Vector Retrieval
Augmented Generation for Efficient Information Extraction"
(arXiv:2408.04948, NVIDIA & BlackRock, 2024)

Provides service dependency graph capabilities:
- Schema definitions (ServiceNode, DependencyEdge)
- Storage (Neo4j, JSON fallback)
- Graph building (from K8s, OTEL)
- Graph retrieval (K-hop expansion)
- HybridRAG fusion (VectorRAG + GraphRAG)
"""

from .schema import (
    ServiceNode,
    DependencyEdge,
    ServiceGraph,
    ServiceType,
    DependencyType,
    Protocol,
)
from .store import Neo4jStore, JsonGraphStore, get_graph_store
from .builder import GraphBuilder, build_otel_demo_graph
from .retriever import GraphRetriever, GraphContext, expand_incident_context
from .fusion import (
    HybridRAGFusion, 
    HybridRAGResult, 
    HybridRAGResponse, 
    create_hybrid_rag,
    # Backward compatibility
    GraphRAGFusion,
    GraphRAGResult,
    GraphRAGResponse,
    create_graph_rag,
)

__all__ = [
    # Schema
    "ServiceNode",
    "DependencyEdge", 
    "ServiceGraph",
    "ServiceType",
    "DependencyType",
    "Protocol",
    # Store
    "Neo4jStore",
    "JsonGraphStore",
    "get_graph_store",
    # Builder
    "GraphBuilder",
    "build_otel_demo_graph",
    # Retriever
    "GraphRetriever",
    "GraphContext",
    "expand_incident_context",
    # HybridRAG Fusion (new names)
    "HybridRAGFusion",
    "HybridRAGResult",
    "HybridRAGResponse",
    "create_hybrid_rag",
    # Backward compatibility
    "GraphRAGFusion",
    "GraphRAGResult",
    "GraphRAGResponse",
    "create_graph_rag",
]