"""Embedding utilities for RAG."""

import asyncio
from typing import Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.config import get_embeddings
from app.agent.tools.chunker import chunk_document
from app.database import async_session_factory
from app.models.reg_doc import RegDoc
from app.models.reg_doc_chunk import RegDocChunk


# Batch size for embedding requests
EMBED_BATCH_SIZE = 10


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a list of texts using OpenRouter embeddings.
    
    Args:
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    embeddings = get_embeddings()
    return await embeddings.aembed_documents(texts)


async def embed_chunks(
    session: AsyncSession,
    chunk_ids: list[int],
) -> int:
    """
    Generate embeddings for specific chunks.
    
    Args:
        session: Database session
        chunk_ids: List of chunk IDs to embed
        
    Returns:
        Number of chunks embedded
    """
    # Fetch chunks
    stmt = select(RegDocChunk).where(RegDocChunk.id.in_(chunk_ids))
    result = await session.execute(stmt)
    chunks = result.scalars().all()
    
    if not chunks:
        return 0
    
    # Batch embed
    texts = [c.content for c in chunks]
    embeddings = await embed_texts(texts)
    
    # Update chunks with embeddings
    for chunk, embedding in zip(chunks, embeddings):
        chunk.embedding = embedding
    
    await session.flush()
    return len(chunks)


async def chunk_and_embed_document(
    session: AsyncSession,
    doc_id: int,
) -> int:
    """
    Chunk a document and generate embeddings for all chunks.
    
    Args:
        session: Database session
        doc_id: Document ID to process
        
    Returns:
        Number of chunks created
    """
    # Fetch document
    doc = await session.get(RegDoc, doc_id)
    if not doc or not doc.text_content:
        return 0
    
    # Delete existing chunks
    await session.execute(
        text("DELETE FROM reg_doc_chunk WHERE reg_doc_id = :doc_id"),
        {"doc_id": doc_id}
    )
    
    # Create new chunks
    chunk_data = chunk_document(doc_id, doc.text_content, doc.title)
    
    if not chunk_data:
        return 0
    
    # Create chunk objects
    chunks = [RegDocChunk(**data) for data in chunk_data]
    session.add_all(chunks)
    await session.flush()
    
    # Generate embeddings in batches
    for i in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[i:i + EMBED_BATCH_SIZE]
        texts = [c.content for c in batch]
        
        try:
            embeddings = await embed_texts(texts)
            for chunk, embedding in zip(batch, embeddings):
                chunk.embedding = embedding
        except Exception as e:
            print(f"Embedding batch failed: {e}")
            # Continue without embeddings - FTS will still work
    
    await session.flush()
    return len(chunks)


async def embed_all_documents() -> dict:
    """
    Chunk and embed all documents that don't have chunks yet.
    
    Returns:
        Summary of processing results
    """
    results = {
        "processed": 0,
        "chunks_created": 0,
        "errors": [],
    }
    
    async with async_session_factory() as session:
        # Find documents without chunks
        stmt = text("""
            SELECT d.id 
            FROM reg_doc d 
            LEFT JOIN reg_doc_chunk c ON d.id = c.reg_doc_id
            WHERE c.id IS NULL AND d.text_content IS NOT NULL
        """)
        result = await session.execute(stmt)
        doc_ids = [row[0] for row in result.fetchall()]
        
        print(f"Found {len(doc_ids)} documents to process")
        
        for doc_id in doc_ids:
            try:
                num_chunks = await chunk_and_embed_document(session, doc_id)
                results["processed"] += 1
                results["chunks_created"] += num_chunks
                print(f"  Processed doc {doc_id}: {num_chunks} chunks")
            except Exception as e:
                results["errors"].append({"doc_id": doc_id, "error": str(e)})
                print(f"  Error processing doc {doc_id}: {e}")
        
        await session.commit()
    
    return results
