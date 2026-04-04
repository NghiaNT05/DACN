"""Text chunking for RAG pipeline.

Splits documents into smaller chunks suitable for embedding.
Uses character-based chunking with configurable overlap.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP, MIN_CHUNK_SIZE


@dataclass
class Chunk:
    """A text chunk with metadata."""
    
    text: str
    source_file: str
    chunk_index: int
    start_char: int
    end_char: int
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "text": self.text,
            "source_file": self.source_file,
            "chunk_index": self.chunk_index,
            "start_char": self.start_char,
            "end_char": self.end_char,
        }


def _find_split_point(text: str, target_pos: int, window: int = 50) -> int:
    """Find a good split point near target position.
    
    Prefers splitting at:
    1. Paragraph breaks (double newline)
    2. Sentence endings (. ! ?)
    3. Line breaks
    4. Exact position if no better option
    """
    start = max(0, target_pos - window)
    end = min(len(text), target_pos + window)
    search_area = text[start:end]
    
    # Priority 1: Paragraph break
    para_match = re.search(r'\n\n', search_area)
    if para_match:
        return start + para_match.end()
    
    # Priority 2: Sentence end
    sentence_match = re.search(r'[.!?]\s', search_area)
    if sentence_match:
        return start + sentence_match.end()
    
    # Priority 3: Line break
    line_match = re.search(r'\n', search_area)
    if line_match:
        return start + line_match.end()
    
    # Fallback: exact position
    return target_pos


def chunk_text(
    text: str,
    source_file: str = "unknown",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Split text into overlapping chunks.
    
    Args:
        text: The text to chunk
        source_file: Source file path for metadata
        chunk_size: Target size of each chunk in characters
        chunk_overlap: Overlap between consecutive chunks
        
    Returns:
        List of Chunk objects
    """
    if not text or not text.strip():
        return []
    
    text = text.strip()
    chunks: List[Chunk] = []
    
    start = 0
    chunk_index = 0
    
    while start < len(text):
        # Calculate end position
        end = start + chunk_size
        
        if end >= len(text):
            # Last chunk - take everything remaining
            end = len(text)
        else:
            # Find a good split point
            end = _find_split_point(text, end)
        
        # Extract chunk text
        chunk_text = text[start:end].strip()
        
        # Only keep chunks above minimum size
        if len(chunk_text) >= MIN_CHUNK_SIZE:
            chunks.append(Chunk(
                text=chunk_text,
                source_file=source_file,
                chunk_index=chunk_index,
                start_char=start,
                end_char=end,
            ))
            chunk_index += 1
        
        # Move start position (with overlap)
        # Ensure we always make progress
        new_start = end - chunk_overlap
        if new_start <= start:
            new_start = start + MIN_CHUNK_SIZE  # Force progress
        start = new_start
        
        # Prevent infinite loop
        if start >= len(text) - MIN_CHUNK_SIZE:
            break
    
    return chunks


def chunk_file(
    file_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Read and chunk a file.
    
    Args:
        file_path: Path to the file to chunk
        chunk_size: Target size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of Chunk objects
    """
    try:
        text = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {file_path}: {e}")
        return []
    
    return chunk_text(
        text=text,
        source_file=str(file_path),
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def chunk_directory(
    dir_path: Path,
    patterns: Optional[List[str]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """Chunk all matching files in a directory.
    
    Args:
        dir_path: Directory to scan
        patterns: File patterns to match (default: ["*.md", "*.txt"])
        chunk_size: Target size of each chunk
        chunk_overlap: Overlap between chunks
        
    Returns:
        List of all chunks from all files
    """
    if patterns is None:
        patterns = ["*.md", "*.txt"]
    
    all_chunks: List[Chunk] = []
    
    for pattern in patterns:
        for file_path in dir_path.rglob(pattern):
            if file_path.is_file():
                chunks = chunk_file(
                    file_path=file_path,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                )
                all_chunks.extend(chunks)
    
    return all_chunks
