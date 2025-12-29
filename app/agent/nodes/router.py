"""Query router node - determines search strategy."""

import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.config import ROUTER_SYSTEM_PROMPT, get_llm
from app.agent.state import AgentState, QueryType, RouterResult


# Regex patterns for code detection
CODE_PATTERN = re.compile(r'\b(\d+(?:\.\d+)+)\b')  # e.g., 5.1.2, 6.3.4
SECTION_PATTERN = re.compile(r'\b(?:section|bölüm|madde)\s*(\d+(?:\.\d+)*)\b', re.IGNORECASE)

# Metadata patterns
RG_PATTERN = re.compile(r'\bR\.?G\.?\s*(\d+)\b', re.IGNORECASE)
AE_PATTERN = re.compile(r'\bA\.?E\.?\s*(\d+)\b', re.IGNORECASE)
EK_PATTERN = re.compile(r'\bEK\s*([IVXLCDM]+)\b', re.IGNORECASE)
DATE_PATTERN = re.compile(r'\b\d{2}\.\d{2}\.\d{4}\b')


def _detect_code(query: str) -> str | None:
    """Detect regulation code pattern in query."""
    # First check for explicit section references
    match = SECTION_PATTERN.search(query)
    if match:
        return match.group(1)
    
    # Then check for standalone codes
    match = CODE_PATTERN.search(query)
    if match:
        return match.group(1)
    
    return None


def _detect_metadata(query: str) -> str | None:
    """Detect metadata patterns in query."""
    patterns = [
        (RG_PATTERN, "R.G."),
        (AE_PATTERN, "A.E."),
        (EK_PATTERN, "EK"),
        (DATE_PATTERN, "date"),
    ]
    
    for pattern, label in patterns:
        match = pattern.search(query)
        if match:
            return f"{label} {match.group(0)}"
    
    return None


def route_query(state: dict[str, Any]) -> dict[str, Any]:
    """
    Router node - analyzes query and determines search strategy.
    
    Uses heuristic detection first (fast, deterministic),
    falls back to LLM for ambiguous cases.
    """
    query = state.get("query", "")
    
    print(f"---ROUTING QUERY---")
    print(f"Query: '{query}'")
    
    # Add to query history
    query_history = state.get("query_history", [])
    if query and query not in query_history:
        query_history = query_history + [query]
    
    # Fast heuristic detection
    detected_code = _detect_code(query)
    if detected_code:
        result = RouterResult(
            query_type=QueryType.CODE,
            extracted_code=detected_code,
            extracted_metadata=None,
            reasoning=f"Detected regulation code pattern: {detected_code}",
        )
        return {
            "query": query,  # IMPORTANT: preserve query
            "query_type": QueryType.CODE,
            "router_result": result,
            "query_history": query_history,
        }
    
    detected_metadata = _detect_metadata(query)
    if detected_metadata:
        result = RouterResult(
            query_type=QueryType.METADATA,
            extracted_code=None,
            extracted_metadata=detected_metadata,
            reasoning=f"Detected metadata pattern: {detected_metadata}",
        )
        return {
            "query": query,  # IMPORTANT: preserve query
            "query_type": QueryType.METADATA,
            "router_result": result,
            "query_history": query_history,
        }
    
    # Default to vector search for natural language
    result = RouterResult(
        query_type=QueryType.VECTOR,
        extracted_code=None,
        extracted_metadata=None,
        reasoning="Natural language query - using semantic search",
    )
    
    return {
        "query": query,  # IMPORTANT: preserve query
        "query_type": QueryType.VECTOR,
        "router_result": result,
        "query_history": query_history,
    }
