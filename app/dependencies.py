"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.reg_doc import RegDocRepository
from app.services.reg_doc import RegDocService


# Database session dependency
DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_reg_doc_repository(db: DbSession) -> RegDocRepository:
    """Get RegDoc repository instance."""
    return RegDocRepository(db)


def get_reg_doc_service(
    repository: Annotated[RegDocRepository, Depends(get_reg_doc_repository)]
) -> RegDocService:
    """Get RegDoc service instance."""
    return RegDocService(repository)


# Type aliases for cleaner route signatures
RegDocRepo = Annotated[RegDocRepository, Depends(get_reg_doc_repository)]
RegDocSvc = Annotated[RegDocService, Depends(get_reg_doc_service)]
