"""
Database utilities for PostgreSQL connection and operations.

Pure async implementation — no Streamlit bridge needed.
Reflex event handlers are natively async, so we use asyncpg directly.
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import asyncpg
from asyncpg.pool import Pool
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level pool — initialized once, shared across all requests
# ---------------------------------------------------------------------------

_pool: Optional[Pool] = None


async def initialize_database() -> Pool:
    """Create the connection pool (idempotent)."""
    global _pool
    if _pool is not None and not _pool._closed:
        return _pool

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")

    _pool = await asyncpg.create_pool(
        database_url,
        min_size=2,
        max_size=10,
        max_inactive_connection_lifetime=300,
        command_timeout=60,
    )
    logger.info("Database connection pool initialized")
    return _pool


async def close_database():
    """Close the connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database connection pool closed")


@asynccontextmanager
async def acquire():
    """Acquire a connection from the pool."""
    global _pool
    if _pool is None or _pool._closed:
        await initialize_database()
    async with _pool.acquire() as connection:
        yield connection


# ---------------------------------------------------------------------------
# Document helpers
# ---------------------------------------------------------------------------


async def get_document(document_id: str) -> Optional[Dict[str, Any]]:
    """Get document by ID."""
    async with acquire() as conn:
        result = await conn.fetchrow(
            """
            SELECT id::text, title, source, content, metadata,
                   created_at, updated_at
            FROM documents WHERE id = $1::uuid
            """,
            document_id,
        )
        if result:
            return {
                "id": result["id"],
                "title": result["title"],
                "source": result["source"],
                "content": result["content"],
                "metadata": json.loads(result["metadata"]),
                "created_at": result["created_at"].isoformat(),
                "updated_at": result["updated_at"].isoformat(),
            }
        return None


async def list_documents(
    limit: int = 100,
    offset: int = 0,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """List documents with optional filtering."""
    async with acquire() as conn:
        query = """
            SELECT d.id::text, d.title, d.source, d.metadata,
                   d.created_at, d.updated_at,
                   COUNT(c.id) AS chunk_count
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
        """
        params: list = []
        conditions: list[str] = []

        if metadata_filter:
            conditions.append(f"d.metadata @> ${len(params) + 1}::jsonb")
            params.append(json.dumps(metadata_filter))

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += """
            GROUP BY d.id, d.title, d.source, d.metadata, d.created_at, d.updated_at
            ORDER BY d.created_at DESC
            LIMIT $%d OFFSET $%d
        """ % (len(params) + 1, len(params) + 2)
        params.extend([limit, offset])

        results = await conn.fetch(query, *params)
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "source": row["source"],
                "metadata": json.loads(row["metadata"]),
                "created_at": row["created_at"].isoformat(),
                "updated_at": row["updated_at"].isoformat(),
                "chunk_count": row["chunk_count"],
            }
            for row in results
        ]


async def execute_query(query: str, *params) -> List[Dict[str, Any]]:
    """Execute a custom query."""
    async with acquire() as conn:
        results = await conn.fetch(query, *params)
        return [dict(row) for row in results]


async def test_connection() -> bool:
    """Test database connection."""
    try:
        async with acquire() as conn:
            await conn.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


async def get_total_document_count() -> int:
    """Get total document count."""
    async with acquire() as conn:
        return await conn.fetchval("SELECT COUNT(*) FROM documents")


async def delete_document(document_id: str) -> bool:
    """Delete a document and its chunks (CASCADE)."""
    try:
        async with acquire() as conn:
            await conn.execute("DELETE FROM documents WHERE id = $1::uuid", document_id)
        return True
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}")
        return False


async def clear_all_documents() -> bool:
    """Delete all documents and chunks."""
    try:
        async with acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM chunks")
                await conn.execute("DELETE FROM documents")
        return True
    except Exception as e:
        logger.error(f"Error clearing all documents: {e}")
        return False


async def get_document_chunks(document_id: str) -> List[Dict[str, Any]]:
    """Get all chunks for a document, ordered by index."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id::text, content, chunk_index, metadata, token_count
            FROM chunks
            WHERE document_id = $1::uuid
            ORDER BY chunk_index
            """,
            document_id,
        )
        return [
            {
                "id": row["id"],
                "content": row["content"],
                "chunk_index": row["chunk_index"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "token_count": row["token_count"],
            }
            for row in rows
        ]


async def get_chunk_details(chunk_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed info about a single chunk."""
    async with acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT c.id::text, c.content, c.chunk_index, c.metadata,
                   c.token_count, c.embedding,
                   d.id::text as document_id, d.title, d.source
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            WHERE c.id = $1::uuid
            """,
            chunk_id,
        )
        if not row:
            return None
        raw_embedding = row["embedding"]
        if raw_embedding:
            # pgvector returns a string like "[0.1,0.2,...]" — parse to float list
            if isinstance(raw_embedding, str):
                embedding = [float(x) for x in raw_embedding.strip("[]").split(",")]
            else:
                embedding = list(raw_embedding)
            embedding_dim = len(embedding)
            embedding_preview = embedding[:50]
        else:
            embedding_dim = 0
            embedding_preview = []
        return {
            "id": row["id"],
            "content": row["content"],
            "chunk_index": row["chunk_index"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "token_count": row["token_count"],
            "embedding_dim": embedding_dim,
            "embedding_preview": embedding_preview,
            "document_id": row["document_id"],
            "title": row["title"],
            "source": row["source"],
        }


async def get_db_stats() -> Dict[str, Any]:
    """Get database statistics."""
    async with acquire() as conn:
        doc_count = await conn.fetchval("SELECT COUNT(*) FROM documents")
        chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
        return {"documents": doc_count, "chunks": chunk_count}


async def search_vectors(embedding_str: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Semantic search using a pre-formatted embedding string."""
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT c.id::text as chunk_id, c.content, c.metadata as chunk_metadata,
                   c.chunk_index,
                   d.id::text as document_id, d.title, d.source,
                   d.metadata as doc_metadata,
                   1 - (c.embedding <=> $1::vector) as similarity
            FROM chunks c
            JOIN documents d ON c.document_id = d.id
            ORDER BY c.embedding <=> $1::vector
            LIMIT $2
            """,
            embedding_str,
            limit,
        )
        return [
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "chunk_metadata": json.loads(row["chunk_metadata"]) if row["chunk_metadata"] else {},
                "chunk_index": row["chunk_index"],
                "document_id": row["document_id"],
                "title": row["title"],
                "source": row["source"],
                "doc_metadata": json.loads(row["doc_metadata"]) if row["doc_metadata"] else {},
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]


async def hybrid_search(
    query_text: str, embedding_str: str, limit: int = 10
) -> List[Dict[str, Any]]:
    """Hybrid search combining keyword (tsvector) and vector (pgvector) with RRF."""
    pool_size = limit * 3  # fetch more candidates from each method for better fusion
    async with acquire() as conn:
        rows = await conn.fetch(
            """
            WITH keyword_results AS (
                SELECT c.id,
                       ROW_NUMBER() OVER (
                           ORDER BY ts_rank_cd(c.search_vector, plainto_tsquery('english', $1)) DESC
                       ) as kw_rank
                FROM chunks c
                WHERE c.search_vector @@ plainto_tsquery('english', $1)
                LIMIT $3
            ),
            vector_results AS (
                SELECT c.id,
                       ROW_NUMBER() OVER (
                           ORDER BY c.embedding <=> $2::vector
                       ) as vec_rank
                FROM chunks c
                WHERE c.embedding IS NOT NULL
                LIMIT $3
            ),
            combined AS (
                SELECT COALESCE(k.id, v.id) as id,
                       COALESCE(1.0 / (60 + k.kw_rank), 0.0)
                         + COALESCE(1.0 / (60 + v.vec_rank), 0.0) as rrf_score
                FROM keyword_results k
                FULL OUTER JOIN vector_results v ON k.id = v.id
            )
            SELECT c.id::text as chunk_id, c.content,
                   c.metadata as chunk_metadata, c.chunk_index,
                   d.id::text as document_id, d.title, d.source,
                   d.metadata as doc_metadata,
                   combined.rrf_score
            FROM combined
            JOIN chunks c ON c.id = combined.id
            JOIN documents d ON c.document_id = d.id
            ORDER BY combined.rrf_score DESC
            LIMIT $4
            """,
            query_text,
            embedding_str,
            pool_size,
            limit,
        )
        return [
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "chunk_metadata": json.loads(row["chunk_metadata"]) if row["chunk_metadata"] else {},
                "chunk_index": row["chunk_index"],
                "document_id": row["document_id"],
                "title": row["title"],
                "source": row["source"],
                "doc_metadata": json.loads(row["doc_metadata"]) if row["doc_metadata"] else {},
                "rrf_score": float(row["rrf_score"]),
            }
            for row in rows
        ]


async def find_similar_chunks(
    embedding_str: str, limit: int = 6, exclude_chunk_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Find chunks similar to a given embedding."""
    async with acquire() as conn:
        if exclude_chunk_id:
            rows = await conn.fetch(
                """
                SELECT c.id::text as chunk_id, c.content, d.title, d.source,
                       1 - (c.embedding <=> $1::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.id != $3::uuid
                ORDER BY c.embedding <=> $1::vector
                LIMIT $2
                """,
                embedding_str,
                limit,
                exclude_chunk_id,
            )
        else:
            rows = await conn.fetch(
                """
                SELECT c.id::text as chunk_id, c.content, d.title, d.source,
                       1 - (c.embedding <=> $1::vector) as similarity
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY c.embedding <=> $1::vector
                LIMIT $2
                """,
                embedding_str,
                limit,
            )
        return [
            {
                "chunk_id": row["chunk_id"],
                "content": row["content"],
                "title": row["title"],
                "source": row["source"],
                "similarity": float(row["similarity"]),
            }
            for row in rows
        ]
