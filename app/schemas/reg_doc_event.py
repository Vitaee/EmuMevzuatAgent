"""Pydantic schemas for RegDocEvent."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class RegDocEventBase(BaseModel):
    """Base schema for document events."""

    event_date: date
    rg_no: Optional[str] = None
    ek: Optional[str] = None
    ae_no: Optional[str] = None


class RegDocEventCreate(RegDocEventBase):
    """Schema for creating a document event."""

    pass


class RegDocEventResponse(RegDocEventBase):
    """Schema for document event response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reg_doc_id: int
