"""Text embedding using sentence-transformers.

Converts text into dense vector representations for semantic search.
"""

from typing import List, Optional, Union
import numpy as np

from .config import DEFAULT_EMBEDDING_MODEL, EMBEDDING_DIMENSION

# Lazy load to avoid import time overhead
_model = None
_model_name = None


def _get_model(model_name: str = DEFAULT_EMBEDDING_MODEL):
    """Get or initialize the embedding model (lazy loading)."""
    global _model, _model_name
    
    if _model is None or _model_name != model_name:
        try:
            from sentence_transformers import SentenceTransformer
            # Force CPU to avoid CUDA compatibility issues
            _model = SentenceTransformer(model_name, device='cpu')
            _model_name = model_name
        except ImportError:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )
    
    return _model


def embed_text(
    text: str,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
) -> List[float]:
    """Embed a single text into a vector.
    
    Args:
        text: Text to embed
        model_name: Name of the sentence-transformers model
        
    Returns:
        List of floats (embedding vector)
    """
    model = _get_model(model_name)
    embedding = model.encode(text, convert_to_numpy=True)
    return embedding.tolist()


def embed_texts(
    texts: List[str],
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 32,
    show_progress: bool = False,
) -> List[List[float]]:
    """Embed multiple texts into vectors.
    
    Args:
        texts: List of texts to embed
        model_name: Name of the sentence-transformers model
        batch_size: Number of texts to process at once
        show_progress: Show progress bar
        
    Returns:
        List of embedding vectors
    """
    if not texts:
        return []
    
    model = _get_model(model_name)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
    )
    return embeddings.tolist()


def compute_similarity(
    embedding1: List[float],
    embedding2: List[float],
) -> float:
    """Compute cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score (0 to 1)
    """
    vec1 = np.array(embedding1)
    vec2 = np.array(embedding2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def get_embedding_dimension(model_name: str = DEFAULT_EMBEDDING_MODEL) -> int:
    """Get the embedding dimension for a model.
    
    Args:
        model_name: Name of the model
        
    Returns:
        Dimension of embedding vectors
    """
    model = _get_model(model_name)
    return model.get_sentence_embedding_dimension()


class Embedder:
    """Wrapper class for embedding operations."""
    
    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL):
        """Initialize embedder with a specific model.
        
        Args:
            model_name: Name of the sentence-transformers model
        """
        self.model_name = model_name
        self._model = None
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            self._model = _get_model(self.model_name)
        return self._model
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()
    
    def embed(self, text: str) -> List[float]:
        """Embed single text."""
        return embed_text(text, self.model_name)
    
    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> List[List[float]]:
        """Embed multiple texts."""
        return embed_texts(
            texts,
            self.model_name,
            batch_size,
            show_progress,
        )
    
    def similarity(
        self,
        embedding1: List[float],
        embedding2: List[float],
    ) -> float:
        """Compute similarity between embeddings."""
        return compute_similarity(embedding1, embedding2)
