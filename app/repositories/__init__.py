"""Repository package."""

from app.repositories.base import BaseRepository
from app.repositories.reg_doc import RegDocRepository

__all__ = ["BaseRepository", "RegDocRepository"]
