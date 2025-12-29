"""LLM and embedding configuration for the agent."""

from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.config import get_settings


@lru_cache
def get_llm(
    model: Optional[str] = None,
    temperature: float = 0.0,
) -> ChatOpenAI:
    """
    Get configured LLM client for OpenRouter.
    
    Args:
        model: Override model name (default from settings)
        temperature: Sampling temperature
        
    Returns:
        Configured ChatOpenAI instance
    """
    settings = get_settings()
    
    return ChatOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=model or settings.llm_model,
        temperature=temperature,
        # OpenRouter specific headers
        default_headers={
            "HTTP-Referer": "https://mevzuat-ai.local",
            "X-Title": "Mevzuat AI Agent",
        },
    )


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """
    Get configured embeddings client for OpenRouter.
    
    Returns:
        Configured OpenAIEmbeddings instance
    """
    settings = get_settings()
    
    return OpenAIEmbeddings(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        model=settings.embedding_model,
    )


def get_embedding_dim() -> int:
    """Get the embedding dimension from settings."""
    return get_settings().embedding_dim


# Prompt templates for structured outputs
ROUTER_SYSTEM_PROMPT = """You are a query router for a legal regulations database.
Analyze the user's query and determine the best search strategy.

Query types:
- CODE: Query mentions a specific regulation code (e.g., "5.1.2", "section 6.3")
- METADATA: Query mentions dates, R.G. numbers, A.E. numbers, or EK references
- VECTOR: General natural language query requiring semantic search

Extract any regulation codes or metadata patterns found in the query.
Be precise and conservative - only mark as CODE if there's a clear code pattern."""

GRADER_SYSTEM_PROMPT = """You are a relevance grader for a legal regulations RAG system.
Given a user query and a document chunk, determine if the chunk is relevant.

Criteria for relevance:
- The chunk directly addresses the query topic
- The chunk contains information that could help answer the query
- The chunk is from a regulation that pertains to the query subject

Be strict: only mark as relevant if the chunk truly helps answer the question.
Provide a brief reason for your decision."""

REWRITER_SYSTEM_PROMPT = """You are a query rewriter for a legal regulations search system.
The previous search did not find relevant results.

Rewrite the query to:
1. Use more specific legal/regulatory terminology
2. Expand abbreviations
3. Include related concepts
4. Be more explicit about the regulation domain

Keep the core intent but make it more searchable."""

GENERATOR_SYSTEM_PROMPT = """You are a legal regulations assistant for EMU University.
Answer questions based ONLY on the provided regulation documents.

CRITICAL RULES:
1. Every substantive claim MUST cite a source with (reg_code, chunk_id)
2. If the documents don't contain enough information, say so explicitly
3. Quote relevant excerpts when making claims
4. Be precise and avoid speculation
5. If asked about something not in the regulations, clearly state that

Format citations as: [Source: code, chunk_id]"""

INSUFFICIENT_EVIDENCE_TEMPLATE = """I searched the EMU regulations database but could not find sufficient information to answer your question.

**Search attempted:**
- Query type: {query_type}
- Queries tried: {queries}
- Regulation codes considered: {codes}

**What I found:**
{findings}

Please try rephrasing your question or ask about a specific regulation section if you know the code (e.g., "What does section 5.1.2 say?")."""
