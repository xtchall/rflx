# CLAUDE.md

## Project Overview

**rflx** is a RAG (Retrieval-Augmented Generation) knowledge base application with a Reflex frontend. It was migrated from a Streamlit project ([docl](https://github.com/xtchall/docl)) to take advantage of Reflex's native async support, component-based architecture, and Python-only full-stack approach.

## Architecture

```
rflx/
  rflx.py                 # App entry — layout, sidebar, routing
  state/                   # Reflex state classes (one per page)
    chat.py                # ChatState — PydanticAI streaming
    home.py                # HomeState — dashboard stats
    documents.py           # DocumentState — upload, ingestion, pagination
    explorer.py            # ExplorerState — search, doc viewer, chunk inspector
    settings.py            # SettingsState — agent config, shared config bridge
  pages/                   # UI components (one per page)
    chat.py, home.py, documents.py, explorer.py, settings.py
utils/
  db_utils.py              # Pure async PostgreSQL pool (asyncpg)
  models.py                # Pydantic data models
  providers.py             # OpenAI model configuration
ingestion/                 # Document processing pipeline
  ingest.py                # Orchestration (DocumentIngestionPipeline)
  chunker.py               # Docling HybridChunker + SimpleChunker fallback
  embedder.py              # OpenAI embedding generation
sql/schema.sql             # PostgreSQL + pgvector schema
cli.py                     # Standalone CLI chat interface
rag_agent.py               # Standalone RAG agent (PydanticAI)
```

## Key Patterns

- **State**: Each page has a `rx.State` subclass. Backend-only vars use underscore prefix (`_message_history`). Use `pydantic.BaseModel` for structured data (not `rx.Base`, which is deprecated).
- **Background tasks**: Long-running operations (LLM streaming, ingestion) use `@rx.event(background=True)` with `async with self:` blocks to push state updates.
- **Database**: Pure async via `asyncpg`. Use `await acquire()` context manager. No sync wrappers needed — Reflex event handlers are natively async.
- **Cross-state config**: `rflx/state/settings.py` has a module-level `_shared_config` dict. `SettingsState` writes to it; `ChatState._get_agent()` reads from it. Setting `_agent = None` forces agent recreation.
- **Agent singleton**: The PydanticAI agent is a module-level lazy singleton in `rflx/state/chat.py`. Created once, reused across sessions.

## Running

```bash
uv run reflex run          # Dev server on localhost:3000
uv run reflex run --env prod  # Production mode
```

Requires `.env` with `DATABASE_URL` and `OPENAI_API_KEY`.

## Engine Files

The `ingestion/`, `utils/models.py`, `utils/providers.py`, `sql/schema.sql`, `rag_agent.py`, and `cli.py` are shared with the docl project. They were copied (not extracted as a package). Changes to engine logic should be considered for both projects.

## Database

PostgreSQL with pgvector extension. Schema in `sql/schema.sql`. Two tables: `documents` and `chunks` (with 1536-dim vector embeddings). Cosine distance operator: `<=>`.

## Common Tasks

- **Add a new page**: Create `rflx/state/newpage.py` + `rflx/pages/newpage.py`, add route in `rflx/rflx.py` via `app.add_page()`, export state in `rflx/state/__init__.py`.
- **Modify agent behavior**: Edit `SYSTEM_PROMPT` in `rflx/state/chat.py` or change via Settings page at runtime.
- **Add ingestion format**: Update `_find_document_files()` patterns and `_read_document()` in `ingestion/ingest.py`.
