"""Chat API endpoint for the CRAG agent."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph import run_agent
from app.agent.state import Citation, GenerationResult

router = APIRouter()


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    
    query: str = Field(..., min_length=1, max_length=2000, description="User's question")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    
    answer: str = Field(description="Generated answer")
    citations: list[dict] = Field(default_factory=list, description="Source citations")
    confidence: float = Field(description="Confidence score 0-1")
    has_sufficient_evidence: bool = Field(description="Whether enough evidence was found")
    query_history: list[str] = Field(default_factory=list, description="Query rewrites if any")
    search_iterations: int = Field(description="Number of search attempts")


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Chat with the regulations assistant.
    
    The agent will:
    1. Analyze your query to determine the best search strategy
    2. Search the regulations database
    3. Evaluate relevance and rewrite query if needed
    4. Generate an answer with citations
    
    Example queries:
    - "What are the regulations for course registration?"
    - "What does section 5.1.2 say?"
    - "What are the requirements for graduate studies?"
    """
    try:
        # Run the agent
        final_state = await run_agent(
            query=request.query,
            thread_id=request.thread_id,
        )
        
        # Extract generation result
        generation = final_state.get("generation")
        
        if generation is None:
            raise HTTPException(
                status_code=500,
                detail="Agent did not produce a response"
            )
        
        # Handle both dict and Pydantic model
        if isinstance(generation, GenerationResult):
            answer = generation.answer
            citations = [c.model_dump() for c in generation.citations]
            confidence = generation.confidence
            has_evidence = generation.has_sufficient_evidence
        elif isinstance(generation, dict):
            answer = generation.get("answer", "")
            citations = generation.get("citations", [])
            confidence = generation.get("confidence", 0.0)
            has_evidence = generation.get("has_sufficient_evidence", False)
        else:
            answer = str(generation)
            citations = []
            confidence = 0.0
            has_evidence = False
        
        return ChatResponse(
            answer=answer,
            citations=citations,
            confidence=confidence,
            has_sufficient_evidence=has_evidence,
            query_history=final_state.get("query_history", []),
            search_iterations=final_state.get("search_iterations", 0),
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Agent error: {str(e)}"
        )


@router.get("/chat/health")
async def chat_health() -> dict:
    """Check if the chat agent is ready."""
    from app.agent.config import get_llm, get_embeddings
    from app.config import get_settings
    
    settings = get_settings()
    
    status = {
        "agent": "ready",
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "openrouter_configured": bool(settings.openrouter_api_key),
    }
    
    if not settings.openrouter_api_key:
        status["warning"] = "OpenRouter API key not configured"
    
    return status
