"""Cross-encoder reranking for improved search precision.

Re-ranks initial retrieval results using a cross-encoder model
that jointly encodes query and document for more accurate scoring.
"""

from typing import List, Tuple, Optional
from dataclasses import dataclass

from .config import RERANKER_MODEL

# Lazy load model
_reranker = None
_reranker_name = None


def _get_reranker(model_name: str = RERANKER_MODEL):
    """Get or initialize the reranker model (lazy loading)."""
    global _reranker, _reranker_name
    
    if _reranker is None or _reranker_name != model_name:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder(model_name, device='cpu')
            _reranker_name = model_name
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for reranking. "
                "Install with: pip install sentence-transformers"
            )
    
    return _reranker


@dataclass
class RerankResult:
    """Result after reranking."""
    text: str
    original_score: float
    rerank_score: float
    metadata: dict
    
    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "original_score": self.original_score,
            "rerank_score": self.rerank_score,
            "metadata": self.metadata,
        }


def rerank(
    query: str,
    documents: List[Tuple[str, float, dict]],  # (text, score, metadata)
    top_k: int = 5,
    model_name: str = RERANKER_MODEL,
) -> List[RerankResult]:
    """Rerank documents using cross-encoder.
    
    Args:
        query: Search query
        documents: List of (text, original_score, metadata) tuples
        top_k: Number of results to return after reranking
        model_name: Cross-encoder model name
        
    Returns:
        List of RerankResult sorted by rerank score
    """
    if not documents:
        return []
    
    reranker = _get_reranker(model_name)
    
    # Prepare query-document pairs
    pairs = [(query, doc[0]) for doc in documents]
    
    # Get rerank scores
    scores = reranker.predict(pairs)
    
    # Combine with original data and sort
    results = []
    for i, (text, orig_score, metadata) in enumerate(documents):
        results.append(RerankResult(
            text=text,
            original_score=orig_score,
            rerank_score=float(scores[i]),
            metadata=metadata,
        ))
    
    # Sort by rerank score (descending)
    results.sort(key=lambda x: x.rerank_score, reverse=True)
    
    return results[:top_k]


class Reranker:
    """Wrapper class for reranking operations."""
    
    def __init__(self, model_name: str = RERANKER_MODEL):
        """Initialize reranker with a specific model."""
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            self._model = _get_reranker(self.model_name)
        return self._model
    
    def rerank(
        self,
        query: str,
        documents: List[Tuple[str, float, dict]],
        top_k: int = 5,
    ) -> List[RerankResult]:
        """Rerank documents."""
        return rerank(query, documents, top_k, self.model_name)
    
    def score_pair(self, query: str, document: str) -> float:
        """Score a single query-document pair."""
        return float(self.model.predict([(query, document)])[0])
