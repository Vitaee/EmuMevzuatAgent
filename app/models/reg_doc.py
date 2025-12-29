"""Regulation Document model."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin

if TYPE_CHECKING:
    from app.models.reg_doc_chunk import RegDocChunk
    from app.models.reg_doc_event import RegDocEvent


class RegDoc(Base, IdMixin):
    """
    Regulation document representing a TOC node and its content.
    
    Stores both hierarchical structure (from TOC) and page content.
    """

    __tablename__ = "reg_doc"

    # TOC hierarchy fields
    code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parent_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    depth: Mapped[int] = mapped_column(nullable=False, default=1)
    sort_key: Mapped[int] = mapped_column(nullable=False, default=0)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")

    # Page content fields
    page_title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_html: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Timestamps
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    events: Mapped[list["RegDocEvent"]] = relationship(
        "RegDocEvent",
        back_populates="reg_doc",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    chunks: Mapped[list["RegDocChunk"]] = relationship(
        "RegDocChunk",
        back_populates="reg_doc",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_reg_doc_language_code", "language", "code", unique=True),
    )

    def __repr__(self) -> str:
        return f"<RegDoc(id={self.id}, code='{self.code}', title='{self.title[:50]}...')>"
