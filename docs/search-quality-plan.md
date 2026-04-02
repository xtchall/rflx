# Search Quality Improvement Plan

## Problem Statement

The chat agent fails on straightforward factual questions even when the answer is explicitly stated in an ingested document. Example: "what was Q4 2024 customer retention rate?" — the answer ("96%") exists in chunk 2 of q4-2024-business-review.pdf but ranks 7th in vector search, outside the default top-5 retrieval window.

### Root Causes

**1. Mixed-topic chunks dilute embeddings**

The executive summary chunk contains 5 unrelated bullet points (revenue, clients, product launch, team size, retention). The embedding becomes an average of all 5 topics, so a query about "retention rate" matches weakly — retention is 1/5th of the semantic signal.

**2. Vector-only search with no keyword fallback**

The system only does cosine similarity on embeddings. A chunk that literally contains "customer retention rate" should be found by a keyword search regardless of what else is in the chunk. The `SearchType` enum defines `KEYWORD` and `HYBRID` values but they are dead code — no implementation exists.

## Solution: Hybrid Search + Chunking Improvements

### Part 1: Hybrid Search (vector + keyword + RRF)

Add PostgreSQL full-text search alongside pgvector, combined with Reciprocal Rank Fusion.

**Schema additions:**
- `tsvector` GENERATED column on `chunks` table (auto-updates, no triggers needed)
- GIN index on the tsvector column
- Upgrade vector index from IVFFlat (lists=1) to HNSW for better recall

**Search approach:**
- Keyword search: `ts_rank_cd()` with `plainto_tsquery()`
- Vector search: cosine distance via pgvector
- Combination: RRF formula `1/(60 + keyword_rank) + 1/(60 + vector_rank)`
- Implemented as a single SQL query with CTEs

**Why RRF:** BM25 scores and cosine similarity are on completely different scales and can't be added directly. RRF converts both to rank-based scores, which are comparable. Research shows hybrid search with RRF improves retrieval precision from ~62% (vector only) to ~84%.

**Impact on the retention rate example:** The keyword component would find "retention rate" as an exact term match in chunk 2, boosting it from rank 7 to top 3 regardless of vector similarity.

### Part 2: Chunking Improvements

**Reduce max_tokens from 512 to 256** — forces the HybridChunker to split tighter, producing more focused chunks. Research shows 256-512 tokens is optimal for factoid queries (simple lookups). The hybrid search compensates for lost context by retrieving multiple focused chunks.

**Enable Docling for markdown files** — currently `.md` files bypass Docling and fall back to SimpleChunker (paragraph splitting). Docling can parse markdown and produce a DoclingDocument, enabling HybridChunker with structure-aware splitting.

**Re-ingestion required** — all documents must be re-processed after chunking changes.

### Files to Modify

| File | Change |
|------|--------|
| `sql/schema.sql` | Add tsvector column, GIN index, HNSW vector index |
| `utils/db_utils.py` | Add `hybrid_search()` with RRF query |
| `rflx/state/chat.py` | Switch `_search_knowledge_base()` to hybrid |
| `rflx/state/explorer.py` | Switch `run_search()` to hybrid |
| `ingestion/chunker.py` | Reduce `max_tokens` default to 256 |
| `ingestion/ingest.py` | Route markdown through Docling converter |

### Verification

1. Run "Q4 2024 customer retention rate" query — should answer "96%" from q4-2024-business-review.pdf
2. Verify keyword search independently finds "retention rate" chunks
3. Verify markdown files now use HybridChunker (check ingestion logs)
4. Compare chunk count before/after re-ingestion (should increase with smaller max_tokens)

## References

- [Hybrid Search in PostgreSQL — ParadeDB](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual)
- [Hybrid search with PostgreSQL and pgvector — Jonathan Katz](https://jkatz05.com/post/postgres/hybrid-search-postgres-pgvector/)
- [Building Hybrid Search for RAG with RRF — DEV Community](https://dev.to/lpossamai/building-hybrid-search-for-rag-combining-pgvector-and-full-text-search-with-reciprocal-rank-fusion-6nk)
- [Best Chunking Strategies for RAG 2025 — Firecrawl](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [Chunking for RAG Best Practices — Unstructured](https://unstructured.io/blog/chunking-for-rag-best-practices)
