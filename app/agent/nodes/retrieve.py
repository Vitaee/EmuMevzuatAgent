"""Retrieval node - hybrid search with RRF fusion."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.config import get_embeddings
from app.agent.state import QueryType, RetrievedChunk
from app.database import async_session_factory


# Search configuration
TOP_K_VECTOR = 20
TOP_K_FTS = 20
TOP_K_FINAL = 12
RRF_K = 60  # RRF constant


async def _embed_query(query: str) -> list[float]:
    """Embed query text using OpenRouter embeddings."""
    embeddings = get_embeddings()
    return await embeddings.aembed_query(query)


async def _search_by_code(
    session: AsyncSession, 
    code: str,
) -> list[RetrievedChunk]:
    """Direct lookup by regulation code."""
    sql = text("""
        SELECT 
            c.id as chunk_id,
            c.reg_doc_id,
            d.code as reg_code,
            d.url,
            c.heading,
            c.content,
            1.0 as score_vec,
            1.0 as score_fts
        FROM reg_doc_chunk c
        JOIN reg_doc d ON c.reg_doc_id = d.id
        WHERE d.code = :code OR d.code LIKE :code_prefix
        ORDER BY c.ordinal
        LIMIT :limit
    """)
    
    result = await session.execute(
        sql, 
        {"code": code, "code_prefix": f"{code}.%", "limit": TOP_K_FINAL}
    )
    rows = result.fetchall()
    
    return [
        RetrievedChunk(
            chunk_id=row.chunk_id,
            reg_doc_id=row.reg_doc_id,
            reg_code=row.reg_code,
            url=row.url,
            heading=row.heading,
            content=row.content,
            score_vec=1.0,
            score_fts=1.0,
            rrf_rank=1.0,
        )
        for row in rows
    ]


async def _search_vector(
    session: AsyncSession,
    query_embedding: list[float],
) -> list[RetrievedChunk]:
    """
    Vector similarity search using pgvector.
    Uses a different approach to handle asyncpg ::vector cast.
    """
    # Convert embedding to PostgreSQL vector string format
    embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
    
    # For asyncpg with pgvector, we need to construct the query differently
    # Use a literal embedding value since bindparam doesn't work well with ::vector cast
    # We sanitize by only using numeric values from our own embedding array
    sql = text(f"""
        SELECT 
            c.id as chunk_id,
            c.reg_doc_id,
            d.code as reg_code,
            d.url,
            c.heading,
            c.content,
            (c.embedding <=> '{embedding_str}'::vector) as vec_distance
        FROM reg_doc_chunk c
        JOIN reg_doc d ON c.reg_doc_id = d.id
        WHERE c.embedding IS NOT NULL
        ORDER BY c.embedding <=> '{embedding_str}'::vector
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"limit": TOP_K_VECTOR})
    rows = result.fetchall()
    
    chunks = []
    for i, row in enumerate(rows):
        # Convert distance to similarity score (lower distance = higher score)
        similarity = 1.0 / (1.0 + float(row.vec_distance)) if row.vec_distance else 0.0
        chunks.append(
            RetrievedChunk(
                chunk_id=row.chunk_id,
                reg_doc_id=row.reg_doc_id,
                reg_code=row.reg_code,
                url=row.url,
                heading=row.heading,
                content=row.content,
                score_vec=similarity,
                score_fts=0.0,
                rrf_rank=1.0 / (RRF_K + i + 1),
            )
        )
    
    return chunks


async def _search_text_only(
    session: AsyncSession,
    query_text: str,
) -> list[RetrievedChunk]:
    """
    Full-text search only.
    """
    if not query_text or not query_text.strip():
        return []
    
    sql = text("""
        SELECT 
            c.id as chunk_id,
            c.reg_doc_id,
            d.code as reg_code,
            d.url,
            c.heading,
            c.content,
            ts_rank(c.content_tsv, plainto_tsquery('english', :query)) as fts_score
        FROM reg_doc_chunk c
        JOIN reg_doc d ON c.reg_doc_id = d.id
        WHERE c.content_tsv @@ plainto_tsquery('english', :query)
        ORDER BY fts_score DESC
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"query": query_text, "limit": TOP_K_FTS})
    rows = result.fetchall()
    
    return [
        RetrievedChunk(
            chunk_id=row.chunk_id,
            reg_doc_id=row.reg_doc_id,
            reg_code=row.reg_code,
            url=row.url,
            heading=row.heading,
            content=row.content,
            score_vec=0.0,
            score_fts=float(row.fts_score) if row.fts_score else 0.5,
            rrf_rank=float(row.fts_score) if row.fts_score else 0.5,
        )
        for row in rows
    ]


async def _search_hybrid(
    session: AsyncSession,
    query: str,
    query_embedding: list[float],
) -> list[RetrievedChunk]:
    """
    Hybrid search combining vector similarity and FTS.
    Uses Reciprocal Rank Fusion (RRF) to combine results.
    """
    # Get vector results
    vec_chunks = await _search_vector(session, query_embedding)
    vec_by_id = {c.chunk_id: (i, c) for i, c in enumerate(vec_chunks)}
    
    # Get FTS results  
    fts_chunks = await _search_text_only(session, query)
    fts_by_id = {c.chunk_id: (i, c) for i, c in enumerate(fts_chunks)}
    
    # Combine with RRF
    all_ids = set(vec_by_id.keys()) | set(fts_by_id.keys())
    
    scored_chunks = []
    for chunk_id in all_ids:
        vec_rank = vec_by_id.get(chunk_id, (999, None))[0]
        fts_rank = fts_by_id.get(chunk_id, (999, None))[0]
        
        # RRF formula
        rrf_score = 0
        if vec_rank < 999:
            rrf_score += 1.0 / (RRF_K + vec_rank + 1)
        if fts_rank < 999:
            rrf_score += 1.0 / (RRF_K + fts_rank + 1)
        
        # Get chunk data from whichever search found it
        chunk_data = vec_by_id.get(chunk_id, (None, None))[1] or fts_by_id.get(chunk_id, (None, None))[1]
        if chunk_data:
            scored_chunks.append((rrf_score, chunk_data))
    
    # Sort by RRF score and take top K
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for rrf_score, chunk in scored_chunks[:TOP_K_FINAL]:
        # Update RRF rank
        results.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                reg_doc_id=chunk.reg_doc_id,
                reg_code=chunk.reg_code,
                url=chunk.url,
                heading=chunk.heading,
                content=chunk.content,
                score_vec=chunk.score_vec,
                score_fts=chunk.score_fts,
                rrf_rank=rrf_score,
            )
        )
    
    return results


async def _search_all_chunks(
    session: AsyncSession,
    limit: int = TOP_K_FINAL,
) -> list[RetrievedChunk]:
    """
    Fallback: return all chunks without filtering.
    """
    sql = text("""
        SELECT 
            c.id as chunk_id,
            c.reg_doc_id,
            d.code as reg_code,
            d.url,
            c.heading,
            c.content
        FROM reg_doc_chunk c
        JOIN reg_doc d ON c.reg_doc_id = d.id
        ORDER BY d.code, c.ordinal
        LIMIT :limit
    """)
    
    result = await session.execute(sql, {"limit": limit})
    rows = result.fetchall()
    
    return [
        RetrievedChunk(
            chunk_id=row.chunk_id,
            reg_doc_id=row.reg_doc_id,
            reg_code=row.reg_code,
            url=row.url,
            heading=row.heading,
            content=row.content,
            score_vec=0.0,
            score_fts=0.0,
            rrf_rank=0.5,
        )
        for row in rows
    ]


async def retrieve_documents(state: dict[str, Any]) -> dict[str, Any]:
    """
    Retrieval node - fetches documents based on query type.
    
    Supports:
    - Direct code lookup
    - Hybrid search (vector + FTS with RRF)
    - FTS fallback
    - All chunks ultimate fallback
    """
    query = state.get("query", "")
    query_type = state.get("query_type", QueryType.VECTOR)
    router_result = state.get("router_result")
    search_iterations = state.get("search_iterations", 0)
    
    print(f"---RETRIEVING ({query_type.value if hasattr(query_type, 'value') else query_type})---")
    print(f"Query: '{query[:100] if query else '(empty)'}'")
    
    chunks = []
    
    async with async_session_factory() as session:
        try:
            if query_type == QueryType.CODE and router_result and router_result.extracted_code:
                # Direct code lookup
                print(f"Direct code lookup: {router_result.extracted_code}")
                chunks = await _search_by_code(session, router_result.extracted_code)
            elif query and query.strip():
                # Try hybrid search (vector + FTS)
                try:
                    print("Attempting hybrid search (vector + FTS)...")
                    embedding = await _embed_query(query)
                    chunks = await _search_hybrid(session, query, embedding)
                    print(f"Hybrid search returned {len(chunks)} chunks")
                except Exception as e:
                    print(f"Hybrid search failed: {e}")
                    # Fall back to FTS only
                    print("Falling back to FTS only...")
                    chunks = await _search_text_only(session, query)
                    print(f"FTS returned {len(chunks)} chunks")
            
            # Fallback: get all chunks
            if not chunks:
                print("Falling back to all chunks...")
                chunks = await _search_all_chunks(session)
                print(f"All chunks returned {len(chunks)} chunks")
                    
        except Exception as e:
            print(f"Retrieval error: {e}")
            try:
                chunks = await _search_all_chunks(session)
            except Exception as e2:
                print(f"All chunks fallback also failed: {e2}")
                chunks = []
    
    print(f"Retrieved {len(chunks)} chunks total")
    
    return {
        "query": query,  # IMPORTANT: preserve query
        "retrieval": chunks,
        "search_iterations": search_iterations + 1,
    }
