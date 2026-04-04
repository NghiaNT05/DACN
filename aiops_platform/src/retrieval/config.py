"""Configuration constants for retrieval module."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"
RETRIEVAL_DIR = PROJECT_ROOT / "data" / "retrieval"
VECTOR_DB_DIR = PROJECT_ROOT / "data" / "vector_db"

# Chunking settings - OPTIMIZED
DEFAULT_CHUNK_SIZE = 1000  # increased for better context
DEFAULT_CHUNK_OVERLAP = 200  # 20% overlap for continuity
MIN_CHUNK_SIZE = 100  # minimum chunk size to keep

# Embedding settings - UPGRADED to better model
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
EMBEDDING_DIMENSION = 768  # all-mpnet-base-v2 output dimension

# Cross-encoder for reranking
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Vector store settings
DEFAULT_COLLECTION_NAME = "aiops_knowledge_v2"  # new collection for upgraded embeddings
DEFAULT_DISTANCE_METRIC = "cosine"

# Search settings
DEFAULT_TOP_K = 10  # retrieve more for reranking
DEFAULT_SCORE_THRESHOLD = 0.15  # low threshold for initial retrieval, reranker will filter
RERANK_TOP_K = 5  # final results after reranking
RERANK_SCORE_THRESHOLD = 0.0  # rerank scores are on different scale

# Hybrid search weights
VECTOR_WEIGHT = 0.7  # semantic similarity weight
BM25_WEIGHT = 0.3  # keyword matching weight
