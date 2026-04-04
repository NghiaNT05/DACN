"""BM25 keyword search for hybrid retrieval.

Combines traditional keyword matching with semantic vector search
for better recall on specific terms and jargon.
"""

import re
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter

from .config import KNOWLEDGE_DIR, RETRIEVAL_DIR


def tokenize(text: str) -> List[str]:
    """Simple tokenizer: lowercase, alphanumeric tokens."""
    text = text.lower()
    # Split on non-alphanumeric, keep meaningful tokens
    tokens = re.findall(r'\b[a-z0-9]+\b', text)
    # Remove very short tokens (1-2 chars) except important ones
    important_short = {'k8s', 'io', 'oom', 'cpu', 'ram', 'gb', 'mb', 'ms', 'ns'}
    return [t for t in tokens if len(t) > 2 or t in important_short]


@dataclass
class BM25Result:
    """Result from BM25 search."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "score": self.score,
            "metadata": self.metadata,
        }


class BM25Index:
    """BM25 index for keyword search."""
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """Initialize BM25 with tuning parameters.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0)
            b: Length normalization parameter (0.75 typical)
        """
        self.k1 = k1
        self.b = b
        
        # Index data
        self.documents: List[Dict[str, Any]] = []  # [{id, text, metadata, tokens}]
        self.doc_freqs: Dict[str, int] = {}  # term -> document frequency
        self.avg_doc_len: float = 0.0
        self.corpus_size: int = 0
        
    def add_documents(
        self,
        documents: List[Tuple[str, str, Dict[str, Any]]],  # (id, text, metadata)
    ) -> int:
        """Add documents to the index.
        
        Args:
            documents: List of (chunk_id, text, metadata) tuples
            
        Returns:
            Number of documents added
        """
        total_tokens = 0
        
        for chunk_id, text, metadata in documents:
            tokens = tokenize(text)
            
            self.documents.append({
                'id': chunk_id,
                'text': text,
                'metadata': metadata,
                'tokens': tokens,
                'token_freq': Counter(tokens),
            })
            
            # Update document frequencies
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
            
            total_tokens += len(tokens)
        
        self.corpus_size = len(self.documents)
        self.avg_doc_len = total_tokens / self.corpus_size if self.corpus_size > 0 else 0
        
        return len(documents)
    
    def _idf(self, term: str) -> float:
        """Calculate inverse document frequency."""
        df = self.doc_freqs.get(term, 0)
        if df == 0:
            return 0.0
        # Smooth IDF formula
        return math.log((self.corpus_size - df + 0.5) / (df + 0.5) + 1)
    
    def _score_document(self, query_tokens: List[str], doc: Dict) -> float:
        """Calculate BM25 score for a single document."""
        score = 0.0
        doc_len = len(doc['tokens'])
        
        for token in query_tokens:
            if token not in doc['token_freq']:
                continue
            
            tf = doc['token_freq'][token]
            idf = self._idf(token)
            
            # BM25 formula
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_len)
            
            score += idf * (numerator / denominator)
        
        return score
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        score_threshold: float = 0.0,
    ) -> List[BM25Result]:
        """Search for documents matching the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            score_threshold: Minimum BM25 score
            
        Returns:
            List of BM25Result sorted by score
        """
        if not self.documents:
            return []
        
        query_tokens = tokenize(query)
        if not query_tokens:
            return []
        
        # Score all documents
        scores = []
        for doc in self.documents:
            score = self._score_document(query_tokens, doc)
            if score >= score_threshold:
                scores.append((doc, score))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to results
        results = []
        for doc, score in scores[:top_k]:
            results.append(BM25Result(
                chunk_id=doc['id'],
                text=doc['text'],
                score=score,
                metadata=doc['metadata'],
            ))
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get index statistics."""
        return {
            "corpus_size": self.corpus_size,
            "vocabulary_size": len(self.doc_freqs),
            "avg_doc_length": self.avg_doc_len,
        }
    
    def clear(self) -> None:
        """Clear the index."""
        self.documents = []
        self.doc_freqs = {}
        self.avg_doc_len = 0.0
        self.corpus_size = 0
