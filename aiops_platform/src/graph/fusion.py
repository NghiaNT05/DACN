"""HybridRAG Fusion - combines VectorRAG with GraphRAG.

Based on: "HybridRAG: Integrating Knowledge Graphs and Vector Retrieval
Augmented Generation for Efficient Information Extraction"
(arXiv:2408.04948, NVIDIA & BlackRock, 2024)

Fusion method: Context concatenation (as per paper)
- VectorRAG: Retrieves relevant text chunks via semantic similarity
- GraphRAG: Retrieves related context via knowledge graph traversal
- Combined context is concatenated and passed to LLM
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from .retriever import GraphRetriever, GraphContext, DEFAULT_K_HOP
from .store import get_graph_store, JsonGraphStore

logger = logging.getLogger(__name__)


@dataclass
class HybridRAGResult:
    """Result from HybridRAG search."""
    
    # Core result
    chunk_id: str
    text: str
    source: str
    
    # Score (from vector search)
    score: float
    
    # Graph context
    related_services: List[str] = field(default_factory=list)
    from_graph: bool = False  # True if retrieved via graph expansion
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "source": self.source,
            "score": self.score,
            "related_services": self.related_services,
            "from_graph": self.from_graph,
            "metadata": self.metadata,
        }


@dataclass
class HybridRAGResponse:
    """Complete response from HybridRAG.
    
    Following the HybridRAG paper, this combines:
    - VectorRAG results (semantic similarity)
    - GraphRAG results (knowledge graph context)
    """
    
    query: str
    vector_results: List[HybridRAGResult]  # From VectorRAG
    graph_results: List[HybridRAGResult]   # From GraphRAG (K-hop expansion)
    graph_context: GraphContext
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "vector_results": [r.to_dict() for r in self.vector_results],
            "graph_results": [r.to_dict() for r in self.graph_results],
            "graph_context": self.graph_context.to_dict(),
        }
    
    def get_combined_context(self, max_chunks: int = 5) -> str:
        """Get concatenated context from both sources (as per paper).
        
        HybridRAG fusion = Concatenate VectorRAG + GraphRAG contexts
        """
        # Vector context
        vector_texts = [r.text for r in self.vector_results[:max_chunks]]
        
        # Graph context (deduplicate with vector)
        vector_sources = {r.source for r in self.vector_results[:max_chunks]}
        graph_texts = [
            r.text for r in self.graph_results[:max_chunks]
            if r.source not in vector_sources
        ]
        
        # Concatenate (fusion method from paper)
        all_texts = vector_texts + graph_texts
        return "\n\n---\n\n".join(all_texts)
    
    def get_all_results(self) -> List[HybridRAGResult]:
        """Get all results (vector + graph), deduplicated."""
        seen = set()
        results = []
        for r in self.vector_results + self.graph_results:
            if r.source not in seen:
                seen.add(r.source)
                results.append(r)
        return results
    
    def get_sources(self) -> List[str]:
        """Get unique source files."""
        return list(set(
            r.source for r in self.vector_results + self.graph_results
        ))


class HybridRAGFusion:
    """HybridRAG: Combines VectorRAG with GraphRAG.
    
    Based on arXiv:2408.04948 (NVIDIA & BlackRock, 2024):
    - VectorRAG: Semantic similarity search on text chunks
    - GraphRAG: Knowledge graph traversal for related context
    - Fusion: Concatenate contexts from both sources
    
    This differs from simple RAG by using K-hop graph expansion
    to find related services/entities that may be relevant to the query.
    """
    
    def __init__(
        self,
        vector_retriever,  # HybridRetriever from retrieval module
        graph_retriever: Optional[GraphRetriever] = None,
        k_hop: int = DEFAULT_K_HOP,
    ):
        """Initialize HybridRAG fusion.
        
        Args:
            vector_retriever: HybridRetriever for VectorRAG
            graph_retriever: GraphRetriever for GraphRAG (K-hop)
            k_hop: Default hop distance for graph expansion
        """
        self.vector_retriever = vector_retriever
        self.graph_retriever = graph_retriever or GraphRetriever(k_hop=k_hop)
        self.k_hop = k_hop
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        k_hop: Optional[int] = None,
    ) -> HybridRAGResponse:
        """Perform HybridRAG search (VectorRAG + GraphRAG).
        
        Following the paper's methodology:
        1. VectorRAG: Semantic search on query
        2. GraphRAG: Detect services in query, K-hop expand, get related docs
        3. Fusion: Concatenate both contexts
        
        Args:
            query: Search query (incident description)
            top_k: Number of results per source
            k_hop: Hop distance for graph expansion
            
        Returns:
            HybridRAGResponse with vector and graph results
        """
        k_hop = k_hop or self.k_hop
        
        # ========================================
        # STEP 1: VectorRAG - Semantic similarity
        # ========================================
        vector_search_results = self.vector_retriever.search(
            query,
            top_k=top_k,
            score_threshold=0.1,
        )
        
        vector_results = []
        for vr in vector_search_results.results:
            source = vr.source if hasattr(vr, 'source') else vr.metadata.get('source_file', '')
            score = vr.final_score if hasattr(vr, 'final_score') else vr.score
            
            vector_results.append(HybridRAGResult(
                chunk_id=vr.chunk_id if hasattr(vr, 'chunk_id') else str(id(vr)),
                text=vr.text,
                source=source,
                score=score,
                related_services=[],
                from_graph=False,
                metadata=vr.metadata if hasattr(vr, 'metadata') else {},
            ))
        
        # ========================================
        # STEP 2: GraphRAG - Knowledge graph context
        # ========================================
        # 2a. Detect services mentioned in query
        graph_context = self.graph_retriever.get_context_for_incident(query, k=k_hop)
        
        # 2b. Get documents about related services
        graph_results = []
        if graph_context.related_services:
            # Search for docs about related services
            related_query = " ".join(graph_context.related_services[:5])
            
            graph_search_results = self.vector_retriever.search(
                related_query,
                top_k=top_k,
                score_threshold=0.1,
            )
            
            # Filter to only include docs that mention related services
            all_services = graph_context.get_all_services()
            
            for vr in graph_search_results.results:
                source = vr.source if hasattr(vr, 'source') else vr.metadata.get('source_file', '')
                source_lower = source.lower()
                text_lower = vr.text.lower()
                
                # Check if doc is about a related service
                mentioned_services = [
                    s for s in all_services 
                    if s.lower() in source_lower or s.lower() in text_lower
                ]
                
                if mentioned_services:
                    score = vr.final_score if hasattr(vr, 'final_score') else vr.score
                    
                    graph_results.append(HybridRAGResult(
                        chunk_id=vr.chunk_id if hasattr(vr, 'chunk_id') else str(id(vr)),
                        text=vr.text,
                        source=source,
                        score=score,
                        related_services=mentioned_services,
                        from_graph=True,
                        metadata=vr.metadata if hasattr(vr, 'metadata') else {},
                    ))
        
        # ========================================
        # STEP 3: Return combined results
        # (Fusion = concatenation in get_combined_context)
        # ========================================
        return HybridRAGResponse(
            query=query,
            vector_results=vector_results,
            graph_results=graph_results,
            graph_context=graph_context,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get HybridRAG statistics."""
        return {
            "method": "HybridRAG (arXiv:2408.04948)",
            "fusion": "context_concatenation",
            "k_hop": self.k_hop,
            "graph_stats": self.graph_retriever.get_stats(),
        }


def create_hybrid_rag(
    use_reranker: bool = True,
    k_hop: int = DEFAULT_K_HOP,
) -> HybridRAGFusion:
    """Create a HybridRAG instance with default settings.
    
    Args:
        use_reranker: Whether to use cross-encoder reranking
        k_hop: Default hop distance for graph expansion
        
    Returns:
        Configured HybridRAGFusion instance
    """
    # Import here to avoid circular imports
    from ..retrieval.retriever import HybridRetriever
    
    vector_retriever = HybridRetriever(use_reranker=use_reranker)
    graph_retriever = GraphRetriever(k_hop=k_hop)
    
    return HybridRAGFusion(
        vector_retriever=vector_retriever,
        graph_retriever=graph_retriever,
        k_hop=k_hop,
    )


# Backward compatibility alias
GraphRAGFusion = HybridRAGFusion
GraphRAGResult = HybridRAGResult
GraphRAGResponse = HybridRAGResponse
create_graph_rag = create_hybrid_rag
