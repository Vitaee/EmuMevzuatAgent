"""Regulation Documents API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.dependencies import RegDocSvc
from app.schemas.reg_doc import (
    RegDocCreate,
    RegDocResponse,
    RegDocUpdate,
    RegDocWithDetails,
)

router = APIRouter()


@router.get("/", response_model=list[RegDocResponse])
async def list_documents(
    service: RegDocSvc,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Max records to return"),
) -> list:
    """List all regulation documents with pagination."""
    docs = await service.get_all(skip=skip, limit=limit)
    return list(docs)


@router.get("/count")
async def count_documents(service: RegDocSvc) -> dict:
    """Get total count of regulation documents."""
    count = await service.count()
    return {"count": count}


@router.get("/hierarchy", response_model=list[RegDocResponse])
async def get_hierarchy(
    service: RegDocSvc,
    language: str = Query("en", description="Language code"),
    root_code: Optional[str] = Query(None, description="Root code to start from"),
) -> list:
    """Get document hierarchy (TOC structure)."""
    docs = await service.get_hierarchy(language=language, root_code=root_code)
    return list(docs)


@router.get("/search", response_model=list[RegDocResponse])
async def search_documents(
    service: RegDocSvc,
    q: str = Query(..., min_length=1, description="Search query"),
    language: str = Query("en", description="Language code"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
) -> list:
    """Search documents by title."""
    docs = await service.search(query=q, language=language, limit=limit)
    return list(docs)


@router.get("/code/{code}", response_model=RegDocWithDetails)
async def get_by_code(
    code: str,
    service: RegDocSvc,
    language: str = Query("en", description="Language code"),
) -> RegDocWithDetails:
    """Get a document by its code (e.g., 5.1.2)."""
    doc = await service.get_by_code(code, language)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with code '{code}' not found")
    return doc


@router.get("/{id}", response_model=RegDocWithDetails)
async def get_document(
    id: int,
    service: RegDocSvc,
) -> RegDocWithDetails:
    """Get a document by ID with all details."""
    doc = await service.get_with_details(id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with id {id} not found")
    return doc


@router.post("/", response_model=RegDocResponse, status_code=201)
async def create_document(
    doc_in: RegDocCreate,
    service: RegDocSvc,
) -> RegDocResponse:
    """
    Create a new regulation document.
    
    Can include events and chunks in the request body for batch creation.
    """
    # Check if document already exists
    existing = await service.get_by_code(doc_in.code, doc_in.language)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Document with code '{doc_in.code}' already exists"
        )
    
    doc = await service.create(doc_in)
    return doc


@router.put("/{id}", response_model=RegDocResponse)
async def update_document(
    id: int,
    doc_in: RegDocUpdate,
    service: RegDocSvc,
) -> RegDocResponse:
    """Update an existing document."""
    doc = await service.update(id, doc_in)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document with id {id} not found")
    return doc


@router.delete("/{id}", status_code=204)
async def delete_document(
    id: int,
    service: RegDocSvc,
) -> None:
    """Delete a document and all its related data."""
    deleted = await service.delete(id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Document with id {id} not found")


@router.post("/upsert", response_model=RegDocResponse)
async def upsert_document(
    doc_in: RegDocCreate,
    service: RegDocSvc,
) -> RegDocResponse:
    """
    Insert or update a document by code.
    
    If a document with the same code exists, it will be updated.
    Otherwise, a new document is created.
    """
    doc = await service.upsert(doc_in.code, doc_in.language, doc_in)
    return doc
