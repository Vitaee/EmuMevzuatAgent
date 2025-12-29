"""Answer generation node - synthesizes response with citations."""

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.config import (
    GENERATOR_SYSTEM_PROMPT,
    INSUFFICIENT_EVIDENCE_TEMPLATE,
    get_llm,
)
from app.agent.state import Citation, GenerationResult, RetrievedChunk


def _build_context(chunks: list[RetrievedChunk]) -> str:
    """Build context string from relevant chunks."""
    context_parts = []
    
    for i, chunk in enumerate(chunks):
        context_parts.append(
            f"[Document {i+1}] Code: {chunk.reg_code}, Chunk ID: {chunk.chunk_id}\n"
            f"Heading: {chunk.heading or 'N/A'}\n"
            f"Content: {chunk.content[:2000]}\n"
        )
    
    return "\n---\n".join(context_parts)


def _build_insufficient_response(state: dict[str, Any]) -> GenerationResult:
    """Build response when insufficient evidence is found."""
    query_history = state.get("query_history", [])
    query_type = state.get("query_type", "vector")
    retrieval = state.get("retrieval", [])
    
    # Gather codes that were considered
    codes = list(set(c.reg_code for c in retrieval)) if retrieval else []
    
    # Build findings summary
    if retrieval:
        findings = f"Found {len(retrieval)} document chunks, but none were relevant to your specific question."
    else:
        findings = "No matching documents were found in the database."
    
    answer = INSUFFICIENT_EVIDENCE_TEMPLATE.format(
        query_type=query_type.value if hasattr(query_type, 'value') else str(query_type),
        queries=", ".join(f'"{q}"' for q in query_history[:3]),
        codes=", ".join(codes[:5]) if codes else "None",
        findings=findings,
    )
    
    return GenerationResult(
        answer=answer,
        citations=[],
        confidence=0.0,
        has_sufficient_evidence=False,
    )


async def generate_answer(state: dict[str, Any]) -> dict[str, Any]:
    """
    Generation node - synthesizes final answer with citations.
    
    Rules:
    - Every claim must cite a source
    - If insufficient evidence, return clear explanation
    - Quote relevant excerpts
    """
    query = state.get("query", "")
    relevant_chunks = state.get("relevant_chunks", [])
    retrieval = state.get("retrieval", [])
    
    # Use retrieval as fallback if relevant_chunks is empty
    chunks_to_use = relevant_chunks if relevant_chunks else retrieval
    
    print(f"---GENERATING ANSWER---")
    print(f"Query: '{query}'")
    print(f"Using {len(chunks_to_use)} chunks")
    
    # Check for sufficient evidence
    if not chunks_to_use:
        print("No chunks available - returning insufficient evidence response")
        result = _build_insufficient_response(state)
        return {"generation": result}
    
    # Build context from chunks
    context = _build_context(chunks_to_use[:8])  # Limit to 8 chunks for context
    
    llm = get_llm(temperature=0.1)
    
    prompt = f"""Question: {query}

Relevant Regulation Documents:
{context}

Answer the question based ONLY on the documents above.
For each claim, cite the source like this: [Source: reg_code, chunk_id]
If the documents don't fully answer the question, say so."""

    messages = [
        SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
        HumanMessage(content=prompt),
    ]
    
    try:
        response = await llm.ainvoke(messages)
        answer = response.content
        
        # Extract citations from the chunks used
        citations = [
            Citation(
                reg_code=chunk.reg_code,
                url=chunk.url,
                chunk_id=chunk.chunk_id,
                excerpt=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
            )
            for chunk in chunks_to_use[:8]
        ]
        
        result = GenerationResult(
            answer=answer,
            citations=citations,
            confidence=0.8 if len(chunks_to_use) >= 3 else 0.6,
            has_sufficient_evidence=True,
        )
        
        print(f"Generated answer with {len(citations)} citations")
        return {"generation": result}
        
    except Exception as e:
        print(f"Generation failed: {e}")
        return {
            "generation": GenerationResult(
                answer=f"I encountered an error generating the response: {str(e)}",
                citations=[],
                confidence=0.0,
                has_sufficient_evidence=False,
            ),
            "error": str(e),
        }
