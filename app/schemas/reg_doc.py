"""Pydantic schemas for RegDoc."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.reg_doc_chunk import RegDocChunkCreate, RegDocChunkResponse
from app.schemas.reg_doc_event import RegDocEventCreate, RegDocEventResponse


class RegDocBase(BaseModel):
    """Base schema for regulation documents."""

    code: str = Field(..., max_length=50, description="Document code (e.g., 5.1.2)")
    title: str = Field(..., description="Document title from TOC")
    url: Optional[str] = Field(None, description="Full URL to the document page")
    parent_code: Optional[str] = Field(None, max_length=50, description="Parent code for hierarchy")
    depth: int = Field(1, ge=1, description="Depth in hierarchy (1 = root)")
    sort_key: int = Field(0, ge=0, description="Sort order in TOC")
    language: str = Field("en", max_length=10, description="Language code")


class RegDocCreate(RegDocBase):
    """Schema for creating a regulation document."""

    page_title: Optional[str] = Field(None, description="Title from page content")
    text_content: Optional[str] = Field(None, description="Cleaned text for RAG")
    raw_html: Optional[str] = Field(None, description="Raw HTML for audit/reparse")
    content_sha256: Optional[str] = Field(None, max_length=64, description="Content hash for change detection")
    
    # Nested creation
    events: list[RegDocEventCreate] = Field(default_factory=list)
    chunks: list[RegDocChunkCreate] = Field(default_factory=list)


class RegDocUpdate(BaseModel):
    """Schema for updating a regulation document."""

    title: Optional[str] = None
    url: Optional[str] = None
    parent_code: Optional[str] = None
    depth: Optional[int] = None
    sort_key: Optional[int] = None
    page_title: Optional[str] = None
    text_content: Optional[str] = None
    raw_html: Optional[str] = None
    content_sha256: Optional[str] = None


class RegDocResponse(RegDocBase):
    """Schema for regulation document response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    page_title: Optional[str] = None
    content_sha256: Optional[str] = None
    scraped_at: datetime


class RegDocWithDetails(RegDocResponse):
    """Schema for regulation document with events and chunks."""

    text_content: Optional[str] = None
    events: list[RegDocEventResponse] = Field(default_factory=list)
    chunks: list[RegDocChunkResponse] = Field(default_factory=list)
