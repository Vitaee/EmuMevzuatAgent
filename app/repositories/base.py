"""Base repository with generic CRUD operations."""

from typing import Any, Generic, Optional, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic base repository providing common CRUD operations.
    
    Follows the Repository pattern for data access abstraction.
    """

    def __init__(self, db: AsyncSession, model: Type[ModelType]) -> None:
        self.db = db
        self.model = model

    async def get(self, id: int) -> Optional[ModelType]:
        """Get a single record by ID."""
        return await self.db.get(self.model, id)

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelType]:
        """Get all records with pagination."""
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """Update an existing record."""
        for field, value in obj_in.items():
            if value is not None:
                setattr(db_obj, field, value)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> None:
        """Delete a record."""
        await self.db.delete(db_obj)
        await self.db.flush()

    async def count(self) -> int:
        """Count all records."""
        from sqlalchemy import func

        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
