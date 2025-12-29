"""Document grading node - heuristic-only relevance filtering."""

from typing import Any

from app.agent.state import GradeResult, RetrievedChunk


# Heuristic thresholds
MIN_CONTENT_LENGTH = 50
MIN_SCORE_THRESHOLD = 0.01



def _keyword_match_score(query: str, content: str) -> float:
    """
    Calculate keyword match score between query and content.
    Simple but effective heuristic.
    """
    if not query or not content:
        return 0.0
    
    # Normalize
    query_lower = query.lower()
    content_lower = content.lower()
    
    # Extract query words (skip common words)
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", 
                  "what", "how", "when", "where", "which", "who", "why",
                  "for", "of", "to", "in", "on", "at", "by", "with", "and", "or"}
    query_words = [w for w in query_lower.split() if len(w) > 2 and w not in stop_words]
    
    if not query_words:
        return 0.5  # Default score if no meaningful words
    
    # Count matches
    matches = sum(1 for word in query_words if word in content_lower)
    
    return matches / len(query_words)


def _heuristic_grade(
    query: str,
    chunk: RetrievedChunk,
) -> GradeResult:
    """
    Grade a chunk using heuristics only (no LLM).
    
    Criteria:
    - Content length
    - Retrieval scores
    - Keyword matching
    """
    # Check content length
    if len(chunk.content) < MIN_CONTENT_LENGTH:
        return GradeResult(
            is_relevant=False,
            reason="Content too short",
            confidence=0.9,
        )
    
    # Calculate keyword match
    keyword_score = _keyword_match_score(query, chunk.content)
    
    # Calculate combined score
    retrieval_score = max(chunk.score_vec, chunk.score_fts, chunk.rrf_rank)
    combined_score = (keyword_score * 0.6) + (retrieval_score * 0.4)
    
    # Determine relevance
    # Be lenient - mark as relevant if there's any signal
    is_relevant = combined_score > 0.1 or keyword_score > 0.2 or retrieval_score > 0.3
    
    # If it came from vector or FTS search (not fallback), trust the retriever
    if chunk.score_vec > 0 or chunk.score_fts > 0:
        is_relevant = True
    
    return GradeResult(
        is_relevant=is_relevant,
        reason=f"Keyword: {keyword_score:.2f}, Retrieval: {retrieval_score:.2f}",
        confidence=min(combined_score + 0.3, 1.0),
    )


async def grade_documents(state: dict[str, Any]) -> dict[str, Any]:
    """
    Grading node - filters retrieved chunks using heuristics only.
    
    No LLM calls - just fast keyword matching and score thresholds.
    """
    query = state.get("query", "")
    retrieval = state.get("retrieval", [])
    
    print(f"---GRADING {len(retrieval)} CHUNKS (heuristic only)---")
    
    if not retrieval:
        return {
            "query": query,  # IMPORTANT: preserve query
            "graded_chunks": [],
            "relevant_chunks": [],
        }
    
    graded_chunks = []
    relevant_chunks = []
    
    for chunk in retrieval:
        grade = _heuristic_grade(query, chunk)
        graded_chunks.append((chunk, grade))
        
        if grade.is_relevant:
            relevant_chunks.append(chunk)
            print(f"  ✓ {chunk.reg_code} (chunk {chunk.chunk_id}): {grade.reason}")
        else:
            print(f"  ✗ {chunk.reg_code} (chunk {chunk.chunk_id}): {grade.reason}")
    
    print(f"Relevant chunks: {len(relevant_chunks)}")
    
    return {
        "query": query,  # IMPORTANT: preserve query
        "graded_chunks": graded_chunks,
        "relevant_chunks": relevant_chunks,
    }
