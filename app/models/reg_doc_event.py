"""Regulation Document Event model."""

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, IdMixin

if TYPE_CHECKING:
    from app.models.reg_doc import RegDoc


class RegDocEvent(Base, IdMixin):
    """
    Document event representing enactment or amendment.
    
    Stores metadata extracted from the regulation page's "Brief Title" area:
    - Date (event_date)
    - R.G. number (Official Gazette)
    - EK (Appendix, Roman numeral)
    - A.E. number (Decision number)
    """

    __tablename__ = "reg_doc_event"

    reg_doc_id: Mapped[int] = mapped_column(
        ForeignKey("reg_doc.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    rg_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ek: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    ae_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationship
    reg_doc: Mapped["RegDoc"] = relationship("RegDoc", back_populates="events")

    __table_args__ = (
        Index("ix_reg_doc_event_doc_id", "reg_doc_id"),
    )

    def __repr__(self) -> str:
        return f"<RegDocEvent(id={self.id}, date={self.event_date}, rg={self.rg_no})>"
