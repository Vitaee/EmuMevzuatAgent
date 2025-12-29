"""Service layer for RegDoc business logic."""

import hashlib
from typing import Optional, Sequence

from app.models.reg_doc import RegDoc
from app.repositories.reg_doc import RegDocRepository
from app.schemas.reg_doc import RegDocCreate, RegDocUpdate


class RegDocService:
    """Service for regulation document business logic."""

    def __init__(self, repository: RegDocRepository) -> None:
        self.repository = repository

    async def get(self, id: int) -> Optional[RegDoc]:
        """Get a document by ID."""
        return await self.repository.get(id)

    async def get_with_details(self, id: int) -> Optional[RegDoc]:
        """Get a document with events and chunks."""
        return await self.repository.get_with_details(id)

    async def get_by_code(
        self,
        code: str,
        language: str = "en",
    ) -> Optional[RegDoc]:
        """Get a document by code."""
        return await self.repository.get_by_code(code, language)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[RegDoc]:
        """Get all documents with pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def get_hierarchy(
        self,
        language: str = "en",
        root_code: Optional[str] = None,
    ) -> Sequence[RegDoc]:
        """Get document hierarchy."""
        return await self.repository.get_hierarchy(language, root_code)

    async def create(self, doc_in: RegDocCreate) -> RegDoc:
        """
        Create a new document with events and chunks.
        
        Computes content hash if text_content is provided.
        """
        doc_data = doc_in.model_dump(exclude={"events", "chunks"})
        
        # Compute content hash if text is provided
        if doc_in.text_content:
            doc_data["content_sha256"] = self._compute_hash(doc_in.text_content)
        
        events_data = [e.model_dump() for e in doc_in.events]
        chunks_data = [c.model_dump() for c in doc_in.chunks]
        
        return await self.repository.create_with_relations(
            doc_data, events_data, chunks_data
        )

    async def update(
        self,
        id: int,
        doc_in: RegDocUpdate,
    ) -> Optional[RegDoc]:
        """Update an existing document."""
        db_obj = await self.repository.get(id)
        if not db_obj:
            return None
        
        update_data = doc_in.model_dump(exclude_unset=True)
        
        # Recompute hash if text changed
        if "text_content" in update_data and update_data["text_content"]:
            update_data["content_sha256"] = self._compute_hash(
                update_data["text_content"]
            )
        
        return await self.repository.update(db_obj, update_data)

    async def delete(self, id: int) -> bool:
        """Delete a document and its relations."""
        db_obj = await self.repository.get(id)
        if not db_obj:
            return False
        await self.repository.delete(db_obj)
        return True

    async def upsert(
        self,
        code: str,
        language: str,
        doc_in: RegDocCreate,
    ) -> RegDoc:
        """Insert or update a document by code."""
        doc_data = doc_in.model_dump(exclude={"events", "chunks"})
        
        if doc_in.text_content:
            doc_data["content_sha256"] = self._compute_hash(doc_in.text_content)
        
        return await self.repository.upsert(code, language, doc_data)

    async def search(
        self,
        query: str,
        language: str = "en",
        limit: int = 10,
    ) -> Sequence[RegDoc]:
        """Search documents by text."""
        return await self.repository.search_by_text(query, language, limit)

    async def count(self) -> int:
        """Get total document count."""
        return await self.repository.count()

    @staticmethod
    def _compute_hash(content: str) -> str:
        """Compute SHA256 hash of content for change detection."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()
