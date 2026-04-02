"""Explorer state — semantic search, document viewer, chunk inspector."""

import logging
from typing import Any

import reflex as rx
from pydantic import BaseModel

from utils.db_utils import (
    acquire,
    embed_for_search,
    find_similar_chunks as db_find_similar,
    get_chunk_details as db_get_chunk,
    get_document,
    get_document_chunks,
    hybrid_search,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    chunk_id: str = ""
    document_id: str = ""
    title: str = ""
    source: str = ""
    content: str = ""
    chunk_index: int = 0
    similarity: float = 0.0
    chunk_metadata: dict[str, Any] = {}
    doc_metadata: dict[str, Any] = {}


class ChunkInfo(BaseModel):
    id: str = ""
    content: str = ""
    chunk_index: int = 0
    token_count: int | None = None
    metadata: dict[str, Any] = {}


class DocumentDetail(BaseModel):
    id: str = ""
    title: str = ""
    source: str = ""
    content: str = ""
    created_at: str = ""
    metadata: dict[str, Any] = {}
    chunks: list[ChunkInfo] = []


class ChunkDetail(BaseModel):
    id: str = ""
    content: str = ""
    chunk_index: int = 0
    token_count: int | None = None
    metadata: dict[str, Any] = {}
    embedding_dim: int = 0
    embedding_preview: list[float] = []
    document_id: str = ""
    title: str = ""
    source: str = ""


class SimilarChunk(BaseModel):
    chunk_id: str = ""
    content: str = ""
    title: str = ""
    source: str = ""
    similarity: float = 0.0


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class ExplorerState(rx.State):
    """State for the explorer page."""

    # Tab control
    active_tab: str = "search"

    # Search tab
    search_query: str = ""
    search_limit: int = 10
    search_results: list[SearchResult] = []
    is_searching: bool = False

    # Document viewer
    viewing_document: bool = False
    document_detail: DocumentDetail = DocumentDetail()
    recent_documents: list[dict[str, Any]] = []

    # Chunk inspector
    viewing_chunk: bool = False
    chunk_detail: ChunkDetail = ChunkDetail()
    recent_chunks: list[dict[str, Any]] = []
    total_chunk_count: int = 0
    similar_chunks: list[SimilarChunk] = []
    is_finding_similar: bool = False

    def set_active_tab(self, val: str):
        self.active_tab = val

    def set_search_query(self, val: str):
        self.search_query = val

    def set_search_limit(self, val: str):
        try:
            self.search_limit = int(val)
        except ValueError:
            pass

    @rx.event(background=True)
    async def run_search(self):
        """Run semantic search."""
        async with self:
            query = self.search_query
            limit = self.search_limit
            if not query.strip():
                return
            self.is_searching = True
            self.search_results = []

        try:
            embedding_str = await embed_for_search(query)
            rows = await hybrid_search(query, embedding_str, limit)

            results = [
                SearchResult(
                    chunk_id=r["chunk_id"],
                    document_id=r["document_id"],
                    title=r["title"],
                    source=r["source"],
                    content=r["content"],
                    chunk_index=r["chunk_index"],
                    similarity=r.get("rrf_score", r.get("similarity", 0.0)),
                    chunk_metadata=r.get("chunk_metadata", {}),
                    doc_metadata=r.get("doc_metadata", {}),
                )
                for r in rows
            ]

            async with self:
                self.search_results = results
                self.is_searching = False

        except Exception as e:
            logger.error(f"Search failed: {e}", exc_info=True)
            async with self:
                self.is_searching = False

    # -- Document viewer ---------------------------------------------------

    async def load_recent_documents(self):
        """Load recent documents for the viewer."""

        async with acquire() as conn:
            docs = await conn.fetch(
                """
                SELECT id::text, title, source,
                       (SELECT COUNT(*) FROM chunks WHERE document_id = documents.id) as chunk_count
                FROM documents
                ORDER BY created_at DESC
                """
            )
            self.recent_documents = [dict(d) for d in docs]

    async def view_document(self, document_id: str):
        """Load and display a document."""

        doc = await get_document(document_id)
        if not doc:
            return

        chunks_raw = await get_document_chunks(document_id)
        chunks = [
            ChunkInfo(
                id=c["id"],
                content=c["content"],
                chunk_index=c["chunk_index"],
                token_count=c.get("token_count"),
                metadata=c.get("metadata", {}),
            )
            for c in chunks_raw
        ]

        self.document_detail = DocumentDetail(
            id=doc["id"],
            title=doc["title"],
            source=doc["source"],
            content=doc["content"],
            created_at=doc["created_at"],
            metadata=doc.get("metadata", {}),
            chunks=chunks,
        )
        self.viewing_document = True
        self.active_tab = "documents"

    def back_from_document(self):
        self.viewing_document = False
        self.document_detail = DocumentDetail()

    # -- Chunk inspector ---------------------------------------------------

    async def load_recent_chunks(self):
        """Load recent chunks for the inspector (limited to 50, with total count)."""

        async with acquire() as conn:
            self.total_chunk_count = await conn.fetchval("SELECT COUNT(*) FROM chunks")
            rows = await conn.fetch(
                """
                SELECT c.id::text, c.content, c.chunk_index, c.token_count,
                       d.title, d.source
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY d.created_at DESC, c.chunk_index ASC
                LIMIT 50
                """
            )
            self.recent_chunks = [dict(r) for r in rows]

    async def inspect_chunk(self, chunk_id: str):
        """Load chunk details for the inspector."""

        row = await db_get_chunk(chunk_id)
        if not row:
            return

        self.chunk_detail = ChunkDetail(
            id=row["id"],
            content=row["content"],
            chunk_index=row["chunk_index"],
            token_count=row.get("token_count"),
            metadata=row.get("metadata", {}),
            embedding_dim=row.get("embedding_dim", 0),
            embedding_preview=row.get("embedding_preview", []),
            document_id=row.get("document_id", ""),
            title=row.get("title", ""),
            source=row.get("source", ""),
        )
        self.viewing_chunk = True
        self.active_tab = "chunks"
        self.similar_chunks = []

    def back_from_chunk(self):
        self.viewing_chunk = False
        self.chunk_detail = ChunkDetail()
        self.similar_chunks = []

    @rx.event(background=True)
    async def find_similar(self):
        """Find chunks similar to the currently inspected chunk."""
        async with self:
            self.is_finding_similar = True
            chunk_id = self.chunk_detail.id



        # Get the chunk's embedding
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT embedding FROM chunks WHERE id = $1::uuid", chunk_id
            )

        if not row or not row["embedding"]:
            async with self:
                self.is_finding_similar = False
            return

        raw_embedding = row["embedding"]
        # pgvector returns a string like "[0.1,0.2,...]" — pass through directly
        if isinstance(raw_embedding, str):
            embedding_str = raw_embedding
        else:
            embedding_str = "[" + ",".join(map(str, raw_embedding)) + "]"

        results = await db_find_similar(embedding_str, limit=6, exclude_chunk_id=chunk_id)

        similar = [
            SimilarChunk(
                chunk_id=r["chunk_id"],
                content=r["content"][:500],
                title=r["title"],
                source=r["source"],
                similarity=r["similarity"],
            )
            for r in results
        ]

        async with self:
            self.similar_chunks = similar
            self.is_finding_similar = False
