"""Document management state — upload, list, delete, ingestion."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

import reflex as rx
from pydantic import BaseModel

from ingestion.ingest import DocumentIngestionPipeline
from utils.db_utils import (
    clear_all_documents as db_clear_all,
    delete_document as db_delete,
    get_total_document_count,

    list_documents as db_list_documents,
)
from utils.models import IngestionConfig

logger = logging.getLogger(__name__)


class DocumentInfo(BaseModel):
    """Document summary for the list view."""

    id: str = ""
    title: str = ""
    source: str = ""
    created_at: str = ""
    chunk_count: int = 0
    metadata: dict[str, Any] = {}


class IngestionResultInfo(BaseModel):
    """Result of ingesting a single document."""

    title: str = ""
    chunks_created: int = 0
    errors: list[str] = []


class DocumentState(rx.State):
    """State for the documents page."""

    # Document list
    documents: list[DocumentInfo] = []
    total_count: int = 0
    current_page: int = 0
    docs_per_page: int = 10

    # Upload / ingestion
    is_ingesting: bool = False
    ingestion_progress: float = 0.0
    ingestion_status: str = ""
    ingestion_results: list[IngestionResultInfo] = []
    clean_before_ingest: bool = False

    # Ingestion settings
    chunk_size: int = 1000
    max_chunk_size: int = 2000
    chunk_overlap: int = 200
    use_semantic_chunking: bool = True

    # Confirmation dialog
    show_clear_confirm: bool = False

    # Backend-only
    _temp_dir: str = ""

    async def load_documents(self):
        """Load documents for the current page."""
        self.total_count = await get_total_document_count()
        offset = self.current_page * self.docs_per_page
        rows = await db_list_documents(limit=self.docs_per_page, offset=offset)
        self.documents = [
            DocumentInfo(
                id=r["id"],
                title=r["title"],
                source=r["source"],
                created_at=r["created_at"],
                chunk_count=r["chunk_count"],
                metadata=r.get("metadata", {}),
            )
            for r in rows
        ]

    def next_page(self):
        if (self.current_page + 1) * self.docs_per_page < self.total_count:
            self.current_page += 1
            return DocumentState.load_documents

    def prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            return DocumentState.load_documents

    async def delete_document(self, document_id: str):
        """Delete a document and refresh the list."""
        await db_delete(document_id)
        await self.load_documents()

    def toggle_clear_confirm(self):
        self.show_clear_confirm = not self.show_clear_confirm

    async def clear_all(self):
        """Clear all documents."""
        await db_clear_all()
        self.show_clear_confirm = False
        self.current_page = 0
        await self.load_documents()

    def set_clean_before(self, val: bool):
        self.clean_before_ingest = val

    def set_chunk_size(self, val: str):
        self.chunk_size = int(val)

    def set_max_chunk_size(self, val: str):
        self.max_chunk_size = int(val)

    def set_chunk_overlap(self, val: str):
        self.chunk_overlap = int(val)

    def set_semantic_chunking(self, val: bool):
        self.use_semantic_chunking = val

    async def handle_upload(self, files: list[rx.UploadFile]):
        """Receive uploaded files, save to temp dir, then start ingestion."""
        if self.is_ingesting:
            return

        temp_dir = tempfile.mkdtemp()
        self._temp_dir = temp_dir

        for file in files:
            data = await file.read()
            path = Path(temp_dir) / file.filename
            path.write_bytes(data)

        self.ingestion_status = f"Saved {len(files)} file(s). Starting ingestion..."
        self.ingestion_results = []
        return DocumentState.run_ingestion

    @rx.event(background=True)
    async def run_ingestion(self):
        """Run the ingestion pipeline in the background."""
        async with self:
            self.is_ingesting = True
            self.ingestion_progress = 0.0
            self.ingestion_status = "Initializing pipeline..."

        temp_dir = self._temp_dir

        try:
            config = IngestionConfig(
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                max_chunk_size=self.max_chunk_size,
                use_semantic_chunking=self.use_semantic_chunking,
            )

            pipeline = DocumentIngestionPipeline(
                documents_folder=temp_dir,
                config=config,
                clean_before_ingest=self.clean_before_ingest,
            )

            await pipeline.initialize()

            async with self:
                self.ingestion_status = "Processing documents..."

            results = await pipeline.ingest_documents()

            # Don't call pipeline.close() — it destroys the shared DB pool

            result_infos = [
                IngestionResultInfo(
                    title=r.title,
                    chunks_created=r.chunks_created,
                    errors=r.errors,
                )
                for r in results
            ]

            total_chunks = sum(r.chunks_created for r in results)
            total_errors = sum(len(r.errors) for r in results)

            async with self:
                self.ingestion_results = result_infos
                self.ingestion_progress = 1.0
                if total_errors > 0:
                    self.ingestion_status = (
                        f"Done with errors: {len(results)} docs, "
                        f"{total_chunks} chunks, {total_errors} errors"
                    )
                else:
                    self.ingestion_status = (
                        f"Complete: {len(results)} docs, {total_chunks} chunks"
                    )
                self.is_ingesting = False

            # Refresh document list
            async with self:
                await self.load_documents()

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            async with self:
                self.ingestion_status = f"Error: {e}"
                self.is_ingesting = False
        finally:
            # Clean up temp dir
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass
