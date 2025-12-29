"""Agent state definition with structured types."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class QueryType(str, Enum):
    """Type of query detected by the router."""
    
    CODE = "code"        # Direct regulation code lookup (e.g., "5.1.2")
    METADATA = "metadata"  # Metadata search (e.g., "R.G. 62", dates)
    VECTOR = "vector"     # Semantic search for natural language


class RetrievedChunk(BaseModel):
    """Structured retrieval result with provenance."""
    
    chunk_id: int
    reg_doc_id: int
    reg_code: str
    url: Optional[str] = None
    heading: Optional[str] = None
    content: str
    score_vec: float = 0.0  # Vector similarity score
    score_fts: float = 0.0  # Full-text search score
    rrf_rank: float = 0.0   # Reciprocal Rank Fusion score
    
    class Config:
        frozen = True


class GradeResult(BaseModel):
    """Structured output from document grader."""
    
    is_relevant: bool = Field(description="Whether the document is relevant to the query")
    reason: str = Field(description="Brief explanation for the relevance decision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0-1")


class RouterResult(BaseModel):
    """Structured output from query router."""
    
    query_type: QueryType = Field(description="Detected query type")
    extracted_code: Optional[str] = Field(None, description="Regulation code if detected")
    extracted_metadata: Optional[str] = Field(None, description="Metadata pattern if detected")
    reasoning: str = Field(description="Brief explanation of routing decision")


class Citation(BaseModel):
    """Citation for a claim in the response."""
    
    reg_code: str
    url: Optional[str] = None
    chunk_id: int
    excerpt: str = Field(description="Relevant excerpt from the source")


class GenerationResult(BaseModel):
    """Structured output from answer generator."""
    
    answer: str = Field(description="The generated answer")
    citations: list[Citation] = Field(default_factory=list, description="Sources for claims")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in the answer")
    has_sufficient_evidence: bool = Field(True, description="Whether enough evidence was found")


class AgentState(BaseModel):
    """
    Complete agent state for the CRAG workflow.
    
    Stores all information needed for retrieval, grading, and generation.
    Designed for debugging, replay, and persistence.
    """
    
    # Input
    query: str = Field(description="User's original query")
    thread_id: Optional[str] = Field(None, description="Conversation thread ID")
    
    # Routing
    query_type: QueryType = Field(QueryType.VECTOR, description="Detected query type")
    router_result: Optional[RouterResult] = None
    
    # Retrieval
    retrieval: list[RetrievedChunk] = Field(default_factory=list, description="Retrieved chunks with provenance")
    
    # Grading
    graded_chunks: list[tuple[RetrievedChunk, GradeResult]] = Field(
        default_factory=list, 
        description="Chunks with their grade results"
    )
    relevant_chunks: list[RetrievedChunk] = Field(
        default_factory=list,
        description="Filtered relevant chunks"
    )
    
    # Query History (for debugging and rewrite tracking)
    query_history: list[str] = Field(default_factory=list, description="History of queries including rewrites")
    
    # Control Flow
    search_iterations: int = Field(0, description="Number of retrieval attempts")
    max_iterations: int = Field(3, description="Maximum search iterations before giving up")
    
    # Output
    generation: Optional[GenerationResult] = None
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    error: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def is_relevant(self) -> bool:
        """Check if we have relevant chunks."""
        return len(self.relevant_chunks) > 0
    
    @property
    def has_sufficient_evidence(self) -> bool:
        """Check if we have minimum evidence (at least 2 chunks or 1 distinct document)."""
        if len(self.relevant_chunks) < 1:
            return False
        # Require at least 2 chunks or 2 distinct documents for broad questions
        distinct_docs = len(set(c.reg_doc_id for c in self.relevant_chunks))
        return len(self.relevant_chunks) >= 2 or distinct_docs >= 1
    
    @property
    def should_retry(self) -> bool:
        """Check if we should retry retrieval."""
        return (
            not self.is_relevant 
            and self.search_iterations < self.max_iterations
        )
