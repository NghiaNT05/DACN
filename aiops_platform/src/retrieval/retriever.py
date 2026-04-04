"""High-level retrieval interface.

Provides a simple API for indexing documents and searching.
Supports both basic vector search and advanced hybrid search with reranking.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass

from .config import (
    KNOWLEDGE_DIR,
    RETRIEVAL_DIR,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K,
    DEFAULT_SCORE_THRESHOLD,
    DEFAULT_COLLECTION_NAME,
    RERANK_TOP_K,
)
from .chunker import Chunk, chunk_directory, chunk_file, chunk_text
from .embedder import Embedder
from .vector_store import VectorStore, SearchResult
from .bm25 import BM25Index
from .reranker import Reranker
from .hybrid import HybridSearcher, HybridResult


@dataclass
class RetrievalResult:
    """Result from a retrieval query."""
    
    query: str
    results: List[Union[SearchResult, HybridResult]]
    total_found: int
    search_type: str = "vector"  # "vector", "hybrid", "hybrid+rerank"
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_found": self.total_found,
            "search_type": self.search_type,
        }
    
    def get_context(self, max_chunks: int = 3) -> str:
        """Get concatenated context from top results."""
        chunks = self.results[:max_chunks]
        return "\n\n---\n\n".join([r.text for r in chunks])
    
    def get_sources(self) -> List[str]:
        """Get list of source files."""
        sources = []
        for r in self.results:
            if isinstance(r, HybridResult):
                sources.append(r.source)
            elif hasattr(r, 'metadata'):
                sources.append(r.metadata.get('source_file', 'unknown'))
        return sources


class Retriever:
    """High-level retrieval interface."""
    
    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_dir: Optional[Path] = None,
    ):
        """Initialize retriever.
        
        Args:
            collection_name: Name of the vector store collection
            persist_dir: Directory to persist the vector store
        """
        self.embedder = Embedder()
        self.vector_store = VectorStore(
            collection_name=collection_name,
            persist_dir=persist_dir,
            embedder=self.embedder,
        )
    
    def index_text(
        self,
        text: str,
        source_name: str = "inline",
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> int:
        """Index a text string.
        
        Args:
            text: Text to index
            source_name: Name to identify this text
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            Number of chunks indexed
        """
        chunks = chunk_text(
            text=text,
            source_file=source_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return self.vector_store.add_chunks(chunks)
    
    def index_file(
        self,
        file_path: Path,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> int:
        """Index a single file.
        
        Args:
            file_path: Path to the file
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
            
        Returns:
            Number of chunks indexed
        """
        chunks = chunk_file(
            file_path=file_path,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return self.vector_store.add_chunks(chunks)
    
    def index_directory(
        self,
        dir_path: Path,
        patterns: Optional[List[str]] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        """Index all files in a directory.
        
        Args:
            dir_path: Directory to index
            patterns: File patterns to match
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
            show_progress: Show progress during indexing
            
        Returns:
            Indexing statistics
        """
        chunks = chunk_directory(
            dir_path=dir_path,
            patterns=patterns,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        
        if not chunks:
            return {
                "status": "no_files",
                "directory": str(dir_path),
                "chunks_indexed": 0,
                "files_processed": 0,
            }
        
        # Count unique files
        files = set(c.source_file for c in chunks)
        
        # Add to vector store
        count = self.vector_store.add_chunks(
            chunks,
            show_progress=show_progress,
        )
        
        return {
            "status": "ok",
            "directory": str(dir_path),
            "chunks_indexed": count,
            "files_processed": len(files),
        }
    
    def index_knowledge_base(
        self,
        knowledge_dir: Optional[Path] = None,
        retrieval_dir: Optional[Path] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        """Index the entire knowledge base.
        
        Args:
            knowledge_dir: Path to knowledge directory
            retrieval_dir: Path to retrieval bundles
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
            show_progress: Show progress
            
        Returns:
            Combined indexing statistics
        """
        knowledge_path = knowledge_dir or KNOWLEDGE_DIR
        retrieval_path = retrieval_dir or RETRIEVAL_DIR
        
        results = {
            "knowledge": None,
            "retrieval": None,
            "total_chunks": 0,
            "total_files": 0,
        }
        
        # Index knowledge docs
        if knowledge_path.exists():
            results["knowledge"] = self.index_directory(
                dir_path=knowledge_path,
                patterns=["*.md"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                show_progress=show_progress,
            )
            results["total_chunks"] += results["knowledge"].get("chunks_indexed", 0)
            results["total_files"] += results["knowledge"].get("files_processed", 0)
        
        # Index retrieval bundles
        if retrieval_path.exists():
            results["retrieval"] = self.index_directory(
                dir_path=retrieval_path,
                patterns=["*.txt"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                show_progress=show_progress,
            )
            results["total_chunks"] += results["retrieval"].get("chunks_indexed", 0)
            results["total_files"] += results["retrieval"].get("files_processed", 0)
        
        return results
    
    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        filter_source: Optional[str] = None,
    ) -> RetrievalResult:
        """Search for relevant chunks (basic vector search).
        
        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filter_source: Filter by source file pattern
            
        Returns:
            RetrievalResult with matching chunks
        """
        # Build metadata filter if specified
        filter_metadata = None
        if filter_source:
            filter_metadata = {"source_file": {"$contains": filter_source}}
        
        results = self.vector_store.search(
            query=query,
            top_k=top_k,
            score_threshold=score_threshold,
            filter_metadata=filter_metadata,
        )
        
        return RetrievalResult(
            query=query,
            results=results,
            total_found=len(results),
            search_type="vector",
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            "vector_store": self.vector_store.get_stats(),
            "sources": self.vector_store.list_sources(),
        }
    
    def reset(self) -> None:
        """Reset the vector store (delete all data)."""
        self.vector_store.delete_collection()


class HybridRetriever:
    """Advanced retriever with hybrid search and reranking."""
    
    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_dir: Optional[Path] = None,
        use_reranker: bool = True,
    ):
        """Initialize hybrid retriever.
        
        Args:
            collection_name: Name of the vector store collection
            persist_dir: Directory to persist the vector store
            use_reranker: Whether to use cross-encoder reranking
        """
        self.embedder = Embedder()
        self.vector_store = VectorStore(
            collection_name=collection_name,
            persist_dir=persist_dir,
            embedder=self.embedder,
        )
        self.bm25_index = BM25Index()
        self.reranker = Reranker() if use_reranker else None
        
        self.hybrid_searcher = HybridSearcher(
            vector_store=self.vector_store,
            bm25_index=self.bm25_index,
            reranker=self.reranker,
        )
        
        self._indexed_chunks: List[Chunk] = []  # Keep for BM25 rebuild
    
    def index_knowledge_base(
        self,
        knowledge_dir: Optional[Path] = None,
        retrieval_dir: Optional[Path] = None,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
        show_progress: bool = False,
    ) -> Dict[str, Any]:
        """Index the entire knowledge base into both vector and BM25.
        
        Args:
            knowledge_dir: Path to knowledge directory
            retrieval_dir: Path to retrieval bundles
            chunk_size: Size of chunks
            chunk_overlap: Overlap between chunks
            show_progress: Show progress
            
        Returns:
            Combined indexing statistics
        """
        knowledge_path = knowledge_dir or KNOWLEDGE_DIR
        retrieval_path = retrieval_dir or RETRIEVAL_DIR
        
        all_chunks: List[Chunk] = []
        files_processed = 0
        
        # Collect chunks from knowledge docs
        if knowledge_path.exists():
            knowledge_chunks = chunk_directory(
                dir_path=knowledge_path,
                patterns=["*.md"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            all_chunks.extend(knowledge_chunks)
            files_processed += len(set(c.source_file for c in knowledge_chunks))
        
        # Collect chunks from retrieval bundles
        if retrieval_path.exists():
            retrieval_chunks = chunk_directory(
                dir_path=retrieval_path,
                patterns=["*.txt"],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            all_chunks.extend(retrieval_chunks)
            files_processed += len(set(c.source_file for c in retrieval_chunks))
        
        if not all_chunks:
            return {
                "status": "no_files",
                "chunks_indexed": 0,
                "files_processed": 0,
            }
        
        # Index into both vector store and BM25
        stats = self.hybrid_searcher.index_chunks(
            all_chunks,
            batch_size=100,
            show_progress=show_progress,
        )
        
        self._indexed_chunks = all_chunks
        
        return {
            "status": "ok",
            "chunks_indexed": stats["vector_indexed"],
            "bm25_indexed": stats["bm25_indexed"],
            "files_processed": files_processed,
        }
    
    def search(
        self,
        query: str,
        top_k: int = RERANK_TOP_K,
        score_threshold: float = DEFAULT_SCORE_THRESHOLD,
        use_reranker: bool = True,
    ) -> RetrievalResult:
        """Search using hybrid retrieval with optional reranking.
        
        Args:
            query: Search query
            top_k: Number of final results
            score_threshold: Minimum score threshold
            use_reranker: Whether to use reranking
            
        Returns:
            RetrievalResult with matching chunks
        """
        results = self.hybrid_searcher.search(
            query=query,
            top_k=DEFAULT_TOP_K,  # Get more candidates
            rerank_top_k=top_k,   # Return this many after rerank
            score_threshold=score_threshold,
            use_reranker=use_reranker and self.reranker is not None,
        )
        
        search_type = "hybrid+rerank" if (use_reranker and self.reranker) else "hybrid"
        
        return RetrievalResult(
            query=query,
            results=results,
            total_found=len(results),
            search_type=search_type,
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return self.hybrid_searcher.get_stats()
    
    def reset(self) -> None:
        """Reset all indexes."""
        self.vector_store.delete_collection()
        self.bm25_index.clear()
        self._indexed_chunks = []
