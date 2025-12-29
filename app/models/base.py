from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column



class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """Mixin for adding created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class IdMixin:
    """Mixin for adding auto-increment ID."""

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
