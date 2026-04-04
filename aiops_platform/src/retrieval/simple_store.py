"""Simple JSON-based vector store (no external DB needed).

Alternative to ChromaDB for simpler deployment.
"""

import json
import numpy as np
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict

from .config import VECTOR_DB_DIR
from .embedder import Embedder, compute_similarity
from .chunker import Chunk


@dataclass
class SearchResult:
    """A single search result."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)


class SimpleVectorStore:
    """Simple JSON-based vector store using numpy for similarity."""
    
    def __init__(
        self,
        store_path: Optional[Path] = None,
        embedder: Optional[Embedder] = None,
    ):
        self.store_path = store_path or (VECTOR_DB_DIR / "vectors.json")
        self.embedder = embedder or Embedder()
        self._data = {"chunks": [], "embeddings": [], "metadata": []}
        self._load()
    
    def _load(self):
        """Load existing store from disk."""
        if self.store_path.exists():
            try:
                with open(self.store_path, 'r') as f:
                    self._data = json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
    
    def _save(self):
        """Save store to disk."""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, 'w') as f:
            json.dump(self._data, f)
    
    def add_chunks(
        self,
        chunks: List[Chunk],
        batch_size: int = 32,
        show_progress: bool = False,
    ) -> int:
        """Add chunks to the store."""
        if not chunks:
            return 0
        
        texts = [c.text for c in chunks]
        embeddings = self.embedder.embed_batch(texts, batch_size=batch_size, show_progress=show_progress)
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"{Path(chunk.source_file).stem}_{chunk.chunk_index}"
            self._data["chunks"].append({
                "id": chunk_id,
                "text": chunk.text,
            })
            self._data["embeddings"].append(embeddings[i])
            self._data["metadata"].append({
                "source_file": chunk.source_file,
                "chunk_index": chunk.chunk_index,
            })
        
        self._save()
        return len(chunks)
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        score_threshold: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar chunks."""
        if not self._data["chunks"]:
            return []
        
        query_emb = self.embedder.embed(query)
        
        # Calculate similarities
        scores = []
        for emb in self._data["embeddings"]:
            score = compute_similarity(query_emb, emb)
            scores.append(score)
        
        # Get top-k
        indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in indices:
            if scores[idx] >= score_threshold:
                results.append(SearchResult(
                    chunk_id=self._data["chunks"][idx]["id"],
                    text=self._data["chunks"][idx]["text"],
                    score=scores[idx],
                    metadata=self._data["metadata"][idx],
                ))
        
        return results
    
    def clear(self):
        """Clear all data."""
        self._data = {"chunks": [], "embeddings": [], "metadata": []}
        if self.store_path.exists():
            self.store_path.unlink()
    
    def count(self) -> int:
        """Get number of stored chunks."""
        return len(self._data["chunks"])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics."""
        sources = set()
        for meta in self._data["metadata"]:
            sources.add(meta.get("source_file", "unknown"))
        return {
            "count": self.count(),
            "sources": sorted(sources),
            "store_path": str(self.store_path),
        }
