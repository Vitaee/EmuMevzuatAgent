"""Text chunking utilities for RAG."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class TextChunk:
    """A chunk of text with metadata."""
    
    content: str
    ordinal: int
    heading: Optional[str] = None
    token_count: Optional[int] = None


# Approximate tokens per character (for English text)
CHARS_PER_TOKEN = 4

# Chunking parameters
MAX_CHUNK_TOKENS = 600
OVERLAP_TOKENS = 100
MIN_CHUNK_TOKENS = 50


def _estimate_tokens(text: str) -> int:
    """Estimate token count from character count."""
    return len(text) // CHARS_PER_TOKEN


def _split_by_paragraphs(text: str) -> list[str]:
    """Split text by paragraph breaks."""
    # Split on double newlines or multiple whitespace lines
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _detect_heading(paragraph: str) -> Optional[str]:
    """Detect if a paragraph is a heading."""
    # Short paragraphs that look like headings
    if len(paragraph) < 100:
        # Check for common heading patterns
        if re.match(r'^(Article|Section|Part|Chapter|\d+\.)', paragraph, re.IGNORECASE):
            return paragraph
        # All caps or title case short lines
        if paragraph.isupper() or (len(paragraph.split()) <= 10 and paragraph.istitle()):
            return paragraph
    return None


def chunk_text(
    text: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[TextChunk]:
    """
    Chunk text into overlapping segments for RAG.
    
    Strategy:
    1. Split by paragraphs
    2. Accumulate paragraphs until max_tokens reached
    3. Add overlap from previous chunk
    """
    if not text or not text.strip():
        return []
    
    paragraphs = _split_by_paragraphs(text)
    
    if not paragraphs:
        return []
    
    chunks: list[TextChunk] = []
    current_content: list[str] = []
    current_tokens = 0
    current_heading: Optional[str] = None
    overlap_content: list[str] = []
    
    for para in paragraphs:
        para_tokens = _estimate_tokens(para)
        
        # Check if this is a heading
        heading = _detect_heading(para)
        if heading:
            current_heading = heading
        
        # Check if adding this paragraph would exceed max tokens
        if current_tokens + para_tokens > max_tokens and current_content:
            # Save current chunk
            chunk_text_content = "\n\n".join(current_content)
            chunks.append(TextChunk(
                content=chunk_text_content,
                ordinal=len(chunks),
                heading=current_heading,
                token_count=current_tokens,
            ))
            
            # Calculate overlap
            overlap_chars = overlap_tokens * CHARS_PER_TOKEN
            overlap_content = []
            overlap_size = 0
            
            for p in reversed(current_content):
                if overlap_size + len(p) <= overlap_chars:
                    overlap_content.insert(0, p)
                    overlap_size += len(p)
                else:
                    break
            
            # Start new chunk with overlap
            current_content = overlap_content.copy()
            current_tokens = _estimate_tokens("\n\n".join(current_content))
        
        # Add paragraph to current chunk
        current_content.append(para)
        current_tokens += para_tokens
    
    # Don't forget the last chunk
    if current_content:
        chunk_text_content = "\n\n".join(current_content)
        if _estimate_tokens(chunk_text_content) >= MIN_CHUNK_TOKENS:
            chunks.append(TextChunk(
                content=chunk_text_content,
                ordinal=len(chunks),
                heading=current_heading,
                token_count=_estimate_tokens(chunk_text_content),
            ))
    
    return chunks


def chunk_document(
    doc_id: int,
    text_content: str,
    title: Optional[str] = None,
) -> list[dict]:
    """
    Chunk a document and return data ready for database insertion.
    
    Args:
        doc_id: The reg_doc ID
        text_content: The document text to chunk
        title: Optional document title (used as first chunk heading)
        
    Returns:
        List of dicts ready for RegDocChunk creation
    """
    chunks = chunk_text(text_content)
    
    result = []
    for chunk in chunks:
        result.append({
            "reg_doc_id": doc_id,
            "ordinal": chunk.ordinal,
            "heading": chunk.heading or title,
            "content": chunk.content,
            "token_count": chunk.token_count,
        })
    
    return result
