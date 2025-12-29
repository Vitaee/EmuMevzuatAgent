"""Query rewriter node - reformulates queries for better retrieval."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.config import REWRITER_SYSTEM_PROMPT, get_llm


async def rewrite_query(state: dict[str, Any]) -> dict[str, Any]:
    """
    Rewriter node - reformulates the query for better search results.
    
    Called when grading finds no relevant documents.
    Uses LLM to expand and clarify the query.
    """
    query = state.get("query", "")
    query_history = state.get("query_history", [])
    search_iterations = state.get("search_iterations", 0)
    
    print(f"---REWRITING QUERY (iteration {search_iterations})---")
    print(f"Original: {query}")
    
    llm = get_llm(temperature=0.3)  # Slightly higher temperature for creativity
    
    # Build context from previous attempts
    history_context = ""
    if len(query_history) > 1:
        history_context = f"\n\nPrevious queries that didn't work:\n" + "\n".join(
            f"- {q}" for q in query_history[:-1]
        )
    
    prompt = f"""Original query: {query}
{history_context}

Rewrite this query to find relevant regulation documents at EMU University.
The database contains regulations about:
- Student admissions, exams, registration
- Graduate studies
- Academic staff
- Research projects and publications
- Scholarships and disciplinary matters

Return ONLY the rewritten query, nothing else."""

    messages = [
        SystemMessage(content=REWRITER_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        new_query = response.content.strip()
        
        # Clean up the response
        new_query = new_query.strip('"\'')
        
        # Don't use if it's too similar or empty
        if new_query and new_query.lower() != query.lower():
            print(f"Rewritten: {new_query}")
            return {
                "query": new_query,
                "query_history": query_history + [new_query],
            }
    except Exception as e:
        print(f"Rewrite failed: {e}")
    
    # If rewrite fails, keep original query
    return {
        "query": query,
    }
