"""Regulation Document Chunk model for RAG retrieval."""

from typing import TYPE_CHECKING, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Computed, ForeignKey, Index, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin

if TYPE_CHECKING:
    from app.models.reg_doc import RegDoc


class RegDocChunk(Base, IdMixin):
    """
    Document chunk for RAG retrieval.
    
    Stores chunked text with:
    - Full-text search vector (content_tsv)
    - Embedding vector for semantic search (pgvector)
    """

    __tablename__ = "reg_doc_chunk"

    reg_doc_id: Mapped[int] = mapped_column(
        ForeignKey("reg_doc.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(nullable=False, default=0)
    heading: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[Optional[int]] = mapped_column(nullable=True)

    # Full-text search vector (generated column)
    content_tsv: Mapped[Optional[str]] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
    )

    # Embedding vector (4096 dimensions for qwen/qwen3-embedding-8b)
    embedding: Mapped[Optional[list[float]]] = mapped_column(
        Vector(4096),
        nullable=True,
    )

    # Relationship
    reg_doc: Mapped["RegDoc"] = relationship("RegDoc", back_populates="chunks")

    __table_args__ = (
        Index("ix_reg_doc_chunk_doc_ordinal", "reg_doc_id", "ordinal", unique=True),
        Index("ix_reg_doc_chunk_content_tsv", "content_tsv", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<RegDocChunk(id={self.id}, doc_id={self.reg_doc_id}, ordinal={self.ordinal})>"
