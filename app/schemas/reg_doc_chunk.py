"""Pydantic schemas for RegDocChunk."""

from typing import Optional

from pydantic import BaseModel, ConfigDict


class RegDocChunkBase(BaseModel):
    """Base schema for document chunks."""

    ordinal: int = 0
    heading: Optional[str] = None
    content: str
    token_count: Optional[int] = None


class RegDocChunkCreate(RegDocChunkBase):
    """Schema for creating a document chunk."""

    embedding: Optional[list[float]] = None


class RegDocChunkResponse(RegDocChunkBase):
    """Schema for document chunk response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reg_doc_id: int
    # Note: embedding excluded from response for bandwidth
