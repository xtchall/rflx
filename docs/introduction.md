# Introduction to rflx

## What Is This?

rflx is a RAG (Retrieval-Augmented Generation) knowledge base application. You upload documents, and an AI agent answers questions about them — grounding every response in the actual content and citing its sources.

It's built with [Reflex](https://reflex.dev/) (Python full-stack web framework), [PydanticAI](https://ai.pydantic.dev/) (agent framework), and PostgreSQL with [pgvector](https://github.com/pgvector/pgvector) (vector similarity search).

## How It Works

The system has two phases: **ingestion** (getting documents into the knowledge base) and **querying** (asking questions and getting answers).

### Ingestion

When you upload a document:

1. The file is converted to text. PDFs, Word docs, PowerPoint, Excel, and HTML are processed by [Docling](https://github.com/DS4SD/docling). Audio files (MP3, WAV, etc.) are transcribed by [OpenAI Whisper](https://github.com/openai/whisper). Markdown and plain text are read directly.
2. The text is split into **chunks** — segments of roughly 1000-2000 characters, ideally respecting document structure (headings, paragraphs, sections). Docling's HybridChunker handles this for most formats; markdown and plain text fall back to simpler paragraph-based splitting.
3. Each chunk is sent to OpenAI's embedding API (`text-embedding-3-small`), which returns a 1536-dimensional vector representing the chunk's semantic meaning.
4. The document, its chunks, and their embeddings are stored in PostgreSQL. The pgvector extension enables fast similarity search over the embeddings.

### Querying

When you ask a question in the Chat page:

1. A PydanticAI agent receives your question. The agent has a **search tool** that it decides when and how to use.
2. The agent calls the search tool with a query (which it may rephrase from your original question).
3. The search tool generates an embedding for the query, then finds the most similar chunks in the database using cosine distance.
4. The top matching chunks (with their source documents) are returned to the agent as context.
5. The agent synthesizes an answer from the retrieved chunks and streams it back to you token by token, citing which documents the information came from.

The agent maintains conversation history, so follow-up questions work naturally.

## Pages

### Home (`/`)

Dashboard showing the current state of the knowledge base — document count, chunk count, database connection status, and which AI models are configured. Also has a quick-start guide and list of supported file formats.

### Chat (`/chat`)

The primary interface. Type a question, get a streaming response with source citations. The agent automatically searches the knowledge base before answering. Sources are shown in a collapsible section under each response. Conversation history is maintained for the session.

### Documents (`/documents`)

Three tabs:

- **Upload** — Drag and drop files to ingest them into the knowledge base. Supports PDF, DOCX, PPTX, XLSX, HTML, TXT, MD, and audio formats. Ingestion runs in the background with progress feedback.
- **Document List** — Browse all documents in the knowledge base with pagination. Shows title, source, chunk count, and creation date. Documents can be deleted individually.
- **Ingestion Settings** — Configure how documents are chunked: chunk size, maximum chunk size, overlap between chunks, and whether to use semantic (structure-aware) chunking. Also has a bulk operation to clear all documents.

### Explorer (`/explorer`)

Three tabs for directly inspecting the knowledge base without going through the chat agent:

- **Semantic Search** — Enter a query and see the raw search results with similarity scores. Results are color-coded: green (>0.8), yellow (>0.6), red (<0.6). Useful for understanding what the agent would retrieve for a given question.
- **Document Viewer** — Browse documents and see their full content along with how they were chunked. Each chunk is shown individually with token counts.
- **Chunk Inspector** — Inspect individual chunks in detail: content, metadata, token count, embedding dimensions. Has a "Find Similar Chunks" feature that uses a chunk's own embedding to locate related content elsewhere in the knowledge base.

### Settings (`/settings`)

Four tabs:

- **Agent Settings** — Customize the system prompt that controls agent behavior, adjust temperature (creativity vs determinism), max response tokens, default search result limit, and similarity threshold.
- **Model Configuration** — Shows which LLM and embedding models are currently configured (read from environment variables).
- **API Keys** — Displays the status of required API keys (OpenAI, database URL) with masked previews. Includes a connection test button.
- **UI Preferences** — Toggle display of timestamps, tool calls, and source citations in the chat. Set documents-per-page for the document list.

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Reflex | Python-based reactive UI, compiles to React |
| **Agent** | PydanticAI | LLM orchestration with tool use and streaming |
| **LLM** | OpenAI GPT-4.1-mini | Generates responses (configurable via `LLM_CHOICE` env var) |
| **Embeddings** | OpenAI text-embedding-3-small | 1536-dim vectors for semantic search |
| **Database** | PostgreSQL + pgvector | Document/chunk storage + vector similarity search |
| **Doc Processing** | Docling | Converts PDF, DOCX, PPTX, XLSX, HTML to markdown |
| **Audio** | OpenAI Whisper | Transcribes MP3, WAV, M4A, FLAC to text |
| **DB Driver** | asyncpg | Async PostgreSQL connection pooling |
| **Package Manager** | uv | Fast Python dependency management |

## Project Structure

```
rflx/                      Reflex application
  rflx.py                  App entry point — layout, sidebar, routing
  state/                   State classes (business logic, one per page)
    chat.py                Chat with PydanticAI streaming
    home.py                Dashboard statistics
    documents.py           Upload, ingestion, document list
    explorer.py            Search, document viewer, chunk inspector
    settings.py            Configuration with cross-state bridge
  pages/                   UI components (presentation, one per page)
    chat.py                Chat bubbles, input form, streaming indicator
    home.py                Stat cards, quick start, format list
    documents.py           Upload dropzone, doc cards, settings form
    explorer.py            Search results, document detail, chunk detail
    settings.py            Config forms, API status, preferences

utils/                     Shared utilities (not Reflex-specific)
  db_utils.py              Async PostgreSQL pool + query helpers
  models.py                Pydantic data models (IngestionConfig, etc.)
  providers.py             OpenAI model configuration

ingestion/                 Document processing pipeline
  ingest.py                Orchestrates: read → chunk → embed → store
  chunker.py               Docling HybridChunker + SimpleChunker fallback
  embedder.py              OpenAI embedding generation with batching

sql/schema.sql             Database schema (tables, indexes, functions)
cli.py                     Standalone CLI chat interface
rag_agent.py               Standalone RAG agent (no web UI)
rxconfig.py                Reflex configuration
```

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager
- PostgreSQL with pgvector extension
- OpenAI API key

### Setup

```bash
git clone git@github.com:xtchall/rflx.git
cd rflx
uv sync
```

Create a `.env` file (see `.env.example`):

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
OPENAI_API_KEY=sk-...
```

Initialize the database:

```bash
psql $DATABASE_URL -f sql/schema.sql
```

Start the app:

```bash
uv run reflex init   # first time only
uv run reflex run
```

Open `http://localhost:3000`. Upload some documents on the Documents page, then ask questions on the Chat page.

### CLI Alternative

If you prefer the terminal:

```bash
uv run python cli.py
uv run python cli.py --model gpt-4o --verbose
```

## Origin

This project was migrated from [docl](https://github.com/xtchall/docl), which used Streamlit for the frontend. The migration replaced Streamlit with Reflex while keeping the RAG engine (ingestion pipeline, embeddings, agent, database schema) unchanged. The key architectural improvement: Reflex handles async natively, eliminating the background thread and queue-based streaming workarounds that Streamlit required.
