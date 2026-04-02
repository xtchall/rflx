"""Pydantic models for data validation."""

from pydantic import BaseModel, Field, field_validator


class IngestionConfig(BaseModel):
    """Configuration for document ingestion."""

    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)
    max_chunk_size: int = Field(default=2000, ge=500, le=10000)
    use_semantic_chunking: bool = True

    @field_validator("chunk_overlap")
    @classmethod
    def validate_overlap(cls, v: int, info) -> int:
        chunk_size = info.data.get("chunk_size", 1000)
        if v >= chunk_size:
            raise ValueError(
                f"Chunk overlap ({v}) must be less than chunk size ({chunk_size})"
            )
        return v


class IngestionResult(BaseModel):
    """Result of document ingestion."""

    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    errors: list[str] = Field(default_factory=list)
