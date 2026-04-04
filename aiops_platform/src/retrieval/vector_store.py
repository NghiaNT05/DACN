"""Vector store using ChromaDB.

Stores and queries document embeddings for semantic search.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .config import (
    VECTOR_DB_DIR,
    DEFAULT_COLLECTION_NAME,
    DEFAULT_DISTANCE_METRIC,
)
from .chunker import Chunk
from .embedder import Embedder, embed_texts

# Lazy load ChromaDB
_client = None


@dataclass
class SearchResult:
    """A single search result."""
    
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
        }


def _get_client(persist_dir: Optional[Path] = None):
    """Get or initialize ChromaDB client."""
    global _client
    
    if _client is None:
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError:
            raise ImportError(
                "chromadb is required. "
                "Install with: pip install chromadb"
            )
        
        persist_path = persist_dir or VECTOR_DB_DIR
        persist_path.mkdir(parents=True, exist_ok=True)
        
        _client = chromadb.PersistentClient(
            path=str(persist_path),
            settings=Settings(anonymized_telemetry=False),
        )
    
    return _client


class VectorStore:
    """ChromaDB vector store wrapper."""
    
    def __init__(
        self,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        persist_dir: Optional[Path] = None,
        embedder: Optional[Embedder] = None,
    ):
        """Initialize vector store.
        
        Args:
            collection_name: Name of the ChromaDB collection
            persist_dir: Directory to persist the database
            embedder: Embedder instance (creates new if None)
        """
        self.collection_name = collection_name
        self.persist_dir = persist_dir or VECTOR_DB_DIR
        self.embedder = embedder or Embedder()
        self._collection = None
    
    @property
    def collection(self):
        """Get or create the collection."""
        if self._collection is None:
            client = _get_client(self.persist_dir)
            self._collection = client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": DEFAULT_DISTANCE_METRIC},
            )
        return self._collection
    
    def add_chunks(
        self,
        chunks: List[Chunk],
        batch_size: int = 100,
        show_progress: bool = False,
    ) -> int:
        """Add chunks to the vector store.
        
        Args:
            chunks: List of Chunk objects to add
            batch_size: Number of chunks to process at once
            show_progress: Show progress during embedding
            
        Returns:
            Number of chunks added
        """
        if not chunks:
            return 0
        
        # Prepare data
        ids = []
        texts = []
        metadatas = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{Path(chunk.source_file).stem}_{chunk.chunk_index}"
            ids.append(chunk_id)
            texts.append(chunk.text)
            metadatas.append({
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
                "start_char": chunk.start_char,
                "end_char": chunk.end_char,
            })
        
        # Generate embeddings
        embeddings = self.embedder.embed_batch(
            texts,
            batch_size=batch_size,
            show_progress=show_progress,
        )
        
        # Add to collection in batches
        for i in range(0, len(ids), batch_size):
            batch_end = min(i + batch_size, len(ids))
            self.collection.add(
                ids=ids[i:batch_end],
                embeddings=embeddings[i:batch_end],
                documents=texts[i:batch_end],
                metadatas=metadatas[i:batch_end],
            )
        
        return len(chunks)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar chunks.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            score_threshold: Minimum similarity score
            filter_metadata: Optional metadata filter
            
        Returns:
            List of SearchResult objects
        """
        # Generate query embedding
        query_embedding = self.embedder.embed(query)
        
        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"],
        )
        
        # Convert to SearchResult objects
        search_results = []
        
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                # ChromaDB returns distance, convert to similarity
                # For cosine: similarity = 1 - distance
                distance = results["distances"][0][i] if results["distances"] else 0
                score = 1 - distance
                
                if score >= score_threshold:
                    search_results.append(SearchResult(
                        chunk_id=chunk_id,
                        text=results["documents"][0][i] if results["documents"] else "",
                        score=score,
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                    ))
        
        return search_results
    
    def delete_collection(self) -> None:
        """Delete the entire collection."""
        client = _get_client(self.persist_dir)
        try:
            client.delete_collection(self.collection_name)
            self._collection = None
        except Exception:
            pass  # Collection may not exist
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "collection_name": self.collection_name,
            "count": self.collection.count(),
            "persist_dir": str(self.persist_dir),
        }
    
    def list_sources(self) -> List[str]:
        """List all unique source files in the collection."""
        # Get all metadatas
        result = self.collection.get(include=["metadatas"])
        
        sources = set()
        if result and result["metadatas"]:
            for meta in result["metadatas"]:
                if meta and "source_file" in meta:
                    sources.add(meta["source_file"])
        
        return sorted(sources)
