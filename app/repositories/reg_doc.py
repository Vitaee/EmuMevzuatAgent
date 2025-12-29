"""Repository for RegDoc operations."""

from typing import Optional, Sequence

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.reg_doc import RegDoc
from app.models.reg_doc_chunk import RegDocChunk
from app.models.reg_doc_event import RegDocEvent
from app.repositories.base import BaseRepository


class RegDocRepository(BaseRepository[RegDoc]):
    """Repository for regulation document operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, RegDoc)

    async def get_by_code(
        self,
        code: str,
        language: str = "en",
    ) -> Optional[RegDoc]:
        """Get a document by its code and language."""
        stmt = select(RegDoc).where(
            and_(RegDoc.code == code, RegDoc.language == language)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_details(self, id: int) -> Optional[RegDoc]:
        """Get a document with all its events and chunks loaded."""
        stmt = (
            select(RegDoc)
            .options(
                selectinload(RegDoc.events),
                selectinload(RegDoc.chunks),
            )
            .where(RegDoc.id == id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_hierarchy(
        self,
        language: str = "en",
        root_code: Optional[str] = None,
    ) -> Sequence[RegDoc]:
        """Get document hierarchy, optionally starting from a root code."""
        stmt = select(RegDoc).where(RegDoc.language == language)
        
        if root_code:
            # Get documents that start with this code
            stmt = stmt.where(RegDoc.code.startswith(root_code))
        
        stmt = stmt.order_by(RegDoc.sort_key)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_parent(
        self,
        parent_code: Optional[str],
        language: str = "en",
    ) -> Sequence[RegDoc]:
        """Get all child documents of a parent code."""
        stmt = (
            select(RegDoc)
            .where(
                and_(
                    RegDoc.parent_code == parent_code,
                    RegDoc.language == language,
                )
            )
            .order_by(RegDoc.sort_key)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def upsert(
        self,
        code: str,
        language: str,
        data: dict,
    ) -> RegDoc:
        """Insert or update a document by code and language."""
        existing = await self.get_by_code(code, language)
        
        if existing:
            # Update existing
            for key, value in data.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            # Create new
            data["code"] = code
            data["language"] = language
            return await self.create(data)

    async def create_with_relations(
        self,
        doc_data: dict,
        events_data: list[dict],
        chunks_data: list[dict],
    ) -> RegDoc:
        """Create a document with its events and chunks in one transaction."""
        # Create document
        doc = RegDoc(**doc_data)
        self.db.add(doc)
        await self.db.flush()
        
        # Create events
        for event_data in events_data:
            event = RegDocEvent(reg_doc_id=doc.id, **event_data)
            self.db.add(event)
        
        # Create chunks
        for chunk_data in chunks_data:
            chunk = RegDocChunk(reg_doc_id=doc.id, **chunk_data)
            self.db.add(chunk)
        
        await self.db.flush()
        await self.db.refresh(doc)
        return doc

    async def search_by_text(
        self,
        query: str,
        language: str = "en",
        limit: int = 10,
    ) -> Sequence[RegDoc]:
        """Search documents by title (basic text search)."""
        stmt = (
            select(RegDoc)
            .where(
                and_(
                    RegDoc.language == language,
                    RegDoc.title.ilike(f"%{query}%"),
                )
            )
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
