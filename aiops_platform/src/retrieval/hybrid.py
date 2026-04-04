"""Hybrid search combining vector similarity and BM25 keyword matching.

Provides better retrieval by combining:
- Semantic understanding (vector embeddings)
- Exact keyword matching (BM25)
- Result reranking (cross-encoder)
"""

from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from .config import (
    VECTOR_WEIGHT,
    BM25_WEIGHT,
    DEFAULT_TOP_K,
    RERANK_TOP_K,
    DEFAULT_SCORE_THRESHOLD,
)
from .vector_store import VectorStore, SearchResult
from .bm25 import BM25Index, BM25Result
from .reranker import Reranker, RerankResult
from .chunker import Chunk


@dataclass
class HybridResult:
    """Result from hybrid search."""
    chunk_id: str
    text: str
    vector_score: float
    bm25_score: float
    hybrid_score: float
    rerank_score: Optional[float]
    metadata: Dict[str, Any]
    
    @property
    def final_score(self) -> float:
        """Get the best available score for ranking."""
        if self.rerank_score is not None:
            return self.rerank_score
        return self.hybrid_score
    
    @property
    def source(self) -> str:
        """Get source filename."""
        return self.metadata.get('source_file', 'unknown')
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "vector_score": self.vector_score,
            "bm25_score": self.bm25_score,
            "hybrid_score": self.hybrid_score,
            "rerank_score": self.rerank_score,
            "final_score": self.final_score,
            "source": self.source,
            "metadata": self.metadata,
        }


class HybridSearcher:
    """Hybrid search combining multiple retrieval methods."""
    
    def __init__(
        self,
        vector_store: VectorStore,
        bm25_index: Optional[BM25Index] = None,
        reranker: Optional[Reranker] = None,
        vector_weight: float = VECTOR_WEIGHT,
        bm25_weight: float = BM25_WEIGHT,
    ):
        """Initialize hybrid searcher.
        
        Args:
            vector_store: Vector store for semantic search
            bm25_index: BM25 index for keyword search (optional)
            reranker: Reranker for final scoring (optional)
            vector_weight: Weight for vector similarity (0-1)
            bm25_weight: Weight for BM25 score (0-1)
        """
        self.vector_store = vector_store
        self.bm25_index = bm25_index or BM25Index()
        self.reranker = reranker
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        
        # Normalize weights
        total = self.vector_weight + self.bm25_weight
        self.vector_weight /= total
        self.bm25_weight /= total
    
    def index_chunks(
        self,
        chunks: List[Chunk],
        batch_size: int = 100,
        show_progress: bool = False,
    ) -> Dict[str, int]:
        """Index chunks into both vector store and BM25.
        
        Args:
            chunks: Chunks to index
            batch_size: Batch size for vector indexing
            show_progress: Show progress bar
            
        Returns:
            Statistics about indexed chunks
        """
        # Index in vector store
        vector_count = self.vector_store.add_chunks(
            chunks,
            batch_size=batch_size,
            show_progress=show_progress,
        )
        
        # Index in BM25
        bm25_docs = []
        for chunk in chunks:
            from pathlib import Path
            chunk_id = f"{Path(chunk.source_file).stem}_{chunk.chunk_index}"
            bm25_docs.append((
                chunk_id,
                chunk.text,
                {
                    'source_file': chunk.source_file,
                    'chunk_index': chunk.chunk_index,
                    'start_char': chunk.start_char,
                    'end_char': chunk.end_char,
                }
            ))
        
        bm25_count = self.bm25_index.add_documents(bm25_docs)
        
        return {
            "vector_indexed": vector_count,
            "bm25_indexed": bm25_count,
        }
    
    def _normalize_scores(
        self,
        scores: List[float],
        min_score: float = 0.0,
        max_score: float = 1.0,
    ) -> List[float]:
        """Normalize scores to [0, 1] range."""
        if not scores:
            return []
        
        min_val = min(scores)
        max_val = max(scores)
        
        if max_val == min_val:
            return [0.5] * len(scores)
        
        return [(s - min_val) / (max_val - min_val) for s in scores]
    
    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        rerank_top_k: int = RERANK_TOP_K,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        use_reranker: bool = True,
    ) -> List[HybridResult]:
        """Perform hybrid search with optional reranking.
        
        Args:
            query: Search query
            top_k: Number of candidates to retrieve
            rerank_top_k: Number of final results after reranking
            score_threshold: Minimum score threshold
            use_reranker: Whether to use cross-encoder reranking
            
        Returns:
            List of HybridResult sorted by final score
        """
        # Get vector search results
        vector_results = self.vector_store.search(
            query,
            top_k=top_k,
            score_threshold=0.0,  # Get all, filter later
        )
        
        # Get BM25 results
        bm25_results = self.bm25_index.search(
            query,
            top_k=top_k,
            score_threshold=0.0,
        )
        
        # Merge results
        merged = self._merge_results(vector_results, bm25_results)
        
        # Apply reranking if available
        if use_reranker and self.reranker and merged:
            merged = self._apply_reranking(query, merged, rerank_top_k)
        
        # Filter by threshold and limit
        results = [r for r in merged if r.final_score >= score_threshold]
        results.sort(key=lambda x: x.final_score, reverse=True)
        
        return results[:rerank_top_k]
    
    def _merge_results(
        self,
        vector_results: List[SearchResult],
        bm25_results: List[BM25Result],
    ) -> List[HybridResult]:
        """Merge vector and BM25 results with score fusion."""
        
        # Create lookup dictionaries
        vector_by_id: Dict[str, SearchResult] = {r.chunk_id: r for r in vector_results}
        bm25_by_id: Dict[str, BM25Result] = {r.chunk_id: r for r in bm25_results}
        
        # Get all unique chunk IDs
        all_ids: Set[str] = set(vector_by_id.keys()) | set(bm25_by_id.keys())
        
        # Normalize BM25 scores (they can be > 1)
        if bm25_results:
            bm25_scores = [r.score for r in bm25_results]
            max_bm25 = max(bm25_scores) if bm25_scores else 1.0
        else:
            max_bm25 = 1.0
        
        # Merge with score fusion
        merged = []
        for chunk_id in all_ids:
            vec_result = vector_by_id.get(chunk_id)
            bm25_result = bm25_by_id.get(chunk_id)
            
            vector_score = vec_result.score if vec_result else 0.0
            bm25_score = (bm25_result.score / max_bm25) if bm25_result else 0.0
            
            # Weighted combination
            hybrid_score = (
                self.vector_weight * vector_score +
                self.bm25_weight * bm25_score
            )
            
            # Get text and metadata from whichever result we have
            if vec_result:
                text = vec_result.text
                metadata = vec_result.metadata
            else:
                text = bm25_result.text
                metadata = bm25_result.metadata
            
            merged.append(HybridResult(
                chunk_id=chunk_id,
                text=text,
                vector_score=vector_score,
                bm25_score=bm25_score,
                hybrid_score=hybrid_score,
                rerank_score=None,
                metadata=metadata,
            ))
        
        # Sort by hybrid score
        merged.sort(key=lambda x: x.hybrid_score, reverse=True)
        
        return merged
    
    def _apply_reranking(
        self,
        query: str,
        results: List[HybridResult],
        top_k: int,
    ) -> List[HybridResult]:
        """Apply cross-encoder reranking to results."""
        if not results:
            return []
        
        # Prepare documents for reranking
        docs = [(r.text, r.hybrid_score, r.metadata) for r in results]
        
        # Rerank
        reranked = self.reranker.rerank(query, docs, top_k=top_k)
        
        # Create new HybridResults with rerank scores
        id_to_result = {r.chunk_id: r for r in results}
        
        new_results = []
        for rr in reranked:
            # Find matching original result
            for orig in results:
                if orig.text == rr.text:
                    new_results.append(HybridResult(
                        chunk_id=orig.chunk_id,
                        text=orig.text,
                        vector_score=orig.vector_score,
                        bm25_score=orig.bm25_score,
                        hybrid_score=orig.hybrid_score,
                        rerank_score=rr.rerank_score,
                        metadata=orig.metadata,
                    ))
                    break
        
        return new_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get search statistics."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "bm25_index": self.bm25_index.get_stats(),
            "weights": {
                "vector": self.vector_weight,
                "bm25": self.bm25_weight,
            },
            "has_reranker": self.reranker is not None,
        }
