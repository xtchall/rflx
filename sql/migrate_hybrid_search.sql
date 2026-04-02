-- Migration: Add hybrid search support (tsvector + HNSW index)
-- Run this against an existing database to enable hybrid search.
-- New installations should use schema.sql directly.

-- Add full-text search column (auto-populates for existing rows)
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS search_vector tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

-- GIN index for keyword search
CREATE INDEX IF NOT EXISTS idx_chunks_search_vector ON chunks USING GIN (search_vector);

-- Upgrade vector index from IVFFlat to HNSW for better recall
DROP INDEX IF EXISTS idx_chunks_embedding;
CREATE INDEX idx_chunks_embedding ON chunks USING hnsw (embedding vector_cosine_ops);
