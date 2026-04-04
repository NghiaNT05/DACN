"""Retrieval module for RAG pipeline.

This module provides:
- Text chunking (chunker)
- Text embedding (embedder)
- Vector storage (vector_store)
- BM25 keyword search (bm25)
- Cross-encoder reranking (reranker)
- Hybrid search (hybrid)
- High-level retrieval API (retriever)
"""

from .config import (
    KNOWLEDGE_DIR,
    RETRIEVAL_DIR,
    VECTOR_DB_DIR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_TOP_K,
    RERANKER_MODEL,
    RERANK_TOP_K,
    VECTOR_WEIGHT,
    BM25_WEIGHT,
)
from .chunker import Chunk, chunk_text, chunk_file, chunk_directory
from .embedder import Embedder, embed_text, embed_texts, compute_similarity
from .vector_store import VectorStore, SearchResult
from .bm25 import BM25Index, BM25Result
from .reranker import Reranker, RerankResult, rerank
from .hybrid import HybridSearcher, HybridResult
from .retriever import Retriever, HybridRetriever, RetrievalResult

__all__ = [
    # Config
    "KNOWLEDGE_DIR",
    "RETRIEVAL_DIR",
    "VECTOR_DB_DIR",
    "DEFAULT_CHUNK_SIZE",
    "DEFAULT_CHUNK_OVERLAP",
    "DEFAULT_EMBEDDING_MODEL",
    "DEFAULT_TOP_K",
    "RERANKER_MODEL",
    "RERANK_TOP_K",
    "VECTOR_WEIGHT",
    "BM25_WEIGHT",
    # Chunker
    "Chunk",
    "chunk_text",
    "chunk_file",
    "chunk_directory",
    # Embedder
    "Embedder",
    "embed_text",
    "embed_texts",
    "compute_similarity",
    # Vector Store
    "VectorStore",
    "SearchResult",
    # BM25
    "BM25Index",
    "BM25Result",
    # Reranker
    "Reranker",
    "RerankResult",
    "rerank",
    # Hybrid Search
    "HybridSearcher",
    "HybridResult",
    # Retriever
    "Retriever",
    "HybridRetriever",
    "RetrievalResult",
]
