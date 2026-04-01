# rflx

A RAG (Retrieval-Augmented Generation) knowledge base application built with [Reflex](https://reflex.dev/), [PydanticAI](https://ai.pydantic.dev/), and PostgreSQL/pgvector.

Upload documents, ask questions, and get accurate answers grounded in your knowledge base with source citations.

## Features

- **Chat** — Streaming responses with PydanticAI agent, automatic knowledge base search, source citations
- **Document Management** — Upload PDF, DOCX, PPTX, XLSX, HTML, TXT, MD, and audio files (MP3, WAV, M4A, FLAC with Whisper transcription)
- **Semantic Search** — Direct vector similarity search with cosine distance scoring
- **Document Explorer** — Browse documents, inspect chunks, view embedding metadata, find similar content
- **Configurable** — Tune system prompt, temperature, chunk size, search limits at runtime

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) extension
- OpenAI API key

## Setup

```bash
# Clone and install
git clone git@github.com:xtchall/rflx.git
cd rflx
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Initialize database (run sql/schema.sql against your PostgreSQL instance)
psql $DATABASE_URL -f sql/schema.sql

# Initialize Reflex
uv run reflex init

# Start the app
uv run reflex run
```

The app runs at `http://localhost:3000` with the backend at `http://0.0.0.0:8000`.

## Environment Variables

Create a `.env` file in the project root:

```bash
# Required
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=sk-...

# Optional (defaults shown)
LLM_CHOICE=gpt-4.1-mini
EMBEDDING_MODEL=text-embedding-3-small
```

## Project Structure

```
rflx/                      # Reflex app (state + pages)
  rflx.py                  # App entry point, layout, routing
  state/                   # State classes (one per page)
  pages/                   # UI components (one per page)
utils/                     # Shared utilities
  db_utils.py              # Async PostgreSQL connection pool
  models.py                # Pydantic data models
  providers.py             # OpenAI model configuration
ingestion/                 # Document processing pipeline
  ingest.py                # Ingestion orchestration
  chunker.py               # Docling HybridChunker + fallback
  embedder.py              # OpenAI embedding generation
sql/schema.sql             # Database schema (pgvector)
cli.py                     # Standalone CLI chat interface
rag_agent.py               # Standalone RAG agent
```

## Document Ingestion

Documents can be ingested through the web UI (Documents page) or the CLI:

```bash
# Via CLI
uv run python -m ingestion.ingest --documents /path/to/docs

# Options
uv run python -m ingestion.ingest --documents /path/to/docs \
  --chunk-size 1000 \
  --chunk-overlap 200 \
  --no-clean           # Don't wipe existing data first
```

### Supported Formats

| Format | Method |
|--------|--------|
| PDF, DOCX, PPTX, XLSX, HTML | [Docling](https://github.com/DS4SD/docling) conversion + HybridChunker |
| TXT, MD | Direct read + SimpleChunker (paragraph splitting) |
| MP3, WAV, M4A, FLAC | [Whisper](https://github.com/openai/whisper) transcription + SimpleChunker |

## CLI Chat

A standalone terminal chat interface is also available:

```bash
uv run python cli.py
uv run python cli.py --model gpt-4o --verbose
```

## Database Schema

Two tables with pgvector for semantic search:

- **documents** — id, title, source, content, metadata (JSONB), timestamps
- **chunks** — id, document_id (FK), content, embedding (vector 1536), chunk_index, metadata, token_count

Vector index uses IVFFlat with cosine distance. A `match_chunks()` function provides similarity search.

## Origin

This project was migrated from [docl](https://github.com/xtchall/docl), a Streamlit-based RAG application. The migration replaced the Streamlit frontend with Reflex while keeping the RAG engine (ingestion, embeddings, agent) unchanged. Key architectural change: the Streamlit async bridge (`run_async()`, background event loops, queue-based streaming) was eliminated — Reflex handles async natively.

## License

Private
