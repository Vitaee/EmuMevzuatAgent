"""LangGraph workflow definition for CRAG agent."""

from typing import Any, Literal

from langgraph.graph import END, StateGraph

from app.agent.nodes import (
    generate_answer,
    grade_documents,
    retrieve_documents,
    route_query,
)


def _should_generate_or_fail(state: dict[str, Any]) -> Literal["generate", "fail"]:
    """
    Simple decision: generate if we have chunks, otherwise fail gracefully.
    No rewrite loop to avoid recursion issues.
    """
    relevant_chunks = state.get("relevant_chunks", [])
    retrieval = state.get("retrieval", [])
    
    # If we have relevant chunks, generate
    if relevant_chunks:
        return "generate"
    
    # If we have any retrieval at all, still try to generate
    if retrieval:
        # Copy retrieval to relevant_chunks so generator has something to work with
        return "generate"
    
    return "fail"


def create_graph() -> StateGraph:
    """
    Create the simplified CRAG workflow graph.
    
    Flow (simplified - no rewrite loop):
    1. ROUTE: Analyze query type (code/metadata/vector)
    2. RETRIEVE: Fetch documents based on query type
    3. GRADE: Evaluate chunk relevance (heuristic only)
    4. GENERATE: Generate answer (always attempt)
    """
    # Create graph with dict state (LangGraph standard)
    workflow = StateGraph(dict)
    
    # Add nodes
    workflow.add_node("route", route_query)
    workflow.add_node("retrieve", retrieve_documents)
    workflow.add_node("grade", grade_documents)
    workflow.add_node("generate", generate_answer)
    
    # Build edges - simple linear flow
    workflow.set_entry_point("route")
    workflow.add_edge("route", "retrieve")
    workflow.add_edge("retrieve", "grade")
    
    # After grading, always go to generate (it handles insufficient evidence)
    workflow.add_edge("grade", "generate")
    
    # Generate ends the flow
    workflow.add_edge("generate", END)
    
    return workflow


def compile_graph():
    """Compile the graph for execution."""
    workflow = create_graph()
    return workflow.compile()


async def run_agent(query: str, thread_id: str | None = None) -> dict[str, Any]:
    """
    Run the CRAG agent on a query.
    
    Args:
        query: User's question
        thread_id: Optional thread ID for conversation tracking
        
    Returns:
        Final state with generation result
    """
    graph = compile_graph()
    
    initial_state = {
        "query": query,
        "thread_id": thread_id,
        "query_history": [query],  # Start with query in history
        "retrieval": [],
        "graded_chunks": [],
        "relevant_chunks": [],
        "search_iterations": 0,
        "max_iterations": 1,  # No retries in simplified version
        "generation": None,
        "error": None,
    }
    
    # Run the graph
    final_state = await graph.ainvoke(initial_state)
    
    return final_state
