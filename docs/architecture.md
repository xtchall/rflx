# Architecture & Migration Notes

## Why Reflex Over Streamlit

The original [docl](https://github.com/xtchall/docl) project used Streamlit. The migration to Reflex was motivated by:

- **Native async** — Streamlit requires a background thread + event loop + queue-based bridge (`run_async()`) to handle async operations. Reflex event handlers are natively async, so `await acquire()` and `agent.run_stream()` work directly.
- **Component architecture** — Streamlit reruns the entire script on every interaction. Reflex uses React-style state management with targeted updates, enabling real-time streaming without the queue hack.
- **Deployment separation** — Reflex has its own project structure and dependencies. Mixing two web frameworks in one repo creates dependency and deployment conflicts.

## New Repo vs Branch

A new repository was chosen over a branch because:
- Reflex requires `reflex init` scaffolding (`.web/`, `rxconfig.py`)
- Completely different dependency tree (reflex vs streamlit)
- Different dev server (port 3000 vs 8501)
- No shared frontend code — everything is rewritten

## What Carried Over Unchanged

These files are direct copies from docl and form the shared "engine":

| File | Purpose |
|------|---------|
| `ingestion/ingest.py` | Document processing pipeline |
| `ingestion/chunker.py` | Docling HybridChunker + SimpleChunker |
| `ingestion/embedder.py` | OpenAI embedding generation |
| `utils/models.py` | Pydantic data models |
| `utils/providers.py` | OpenAI model configuration |
| `sql/schema.sql` | PostgreSQL + pgvector schema |
| `rag_agent.py` | Standalone RAG agent |
| `cli.py` | CLI chat interface |

## What Was Rewritten

| Streamlit | Reflex | Notes |
|-----------|--------|-------|
| `utils/db_utils.py` | `utils/db_utils.py` | Removed Streamlit async bridge (persistent loop, `run_async()`, `@st.cache_resource`). Pure async with module-level pool. |
| `frontend/pages/chat.py` | `rflx/state/chat.py` + `rflx/pages/chat.py` | Queue-based streaming replaced with `@rx.event(background=True)` + `async with self:` |
| `frontend/pages/documents.py` | `rflx/state/documents.py` + `rflx/pages/documents.py` | `st.file_uploader` replaced with `rx.upload(on_drop=...)` |
| `frontend/pages/explorer.py` | `rflx/state/explorer.py` + `rflx/pages/explorer.py` | `st.session_state` replaced with `rx.State` vars |
| `frontend/pages/settings.py` | `rflx/state/settings.py` + `rflx/pages/settings.py` | Module-level `_shared_config` dict bridges settings to agent |
| `frontend/app.py` | `rflx/rflx.py` | Sidebar radio nav replaced with link-based routing |

## Key Design Decisions

### State per page
Each page has its own `rx.State` subclass. States are session singletons in Reflex, so `DocumentState.chunk_size` is the same instance whether accessed from `/documents` or `/admin/ingestion`.

### Background events for streaming
PydanticAI's `agent.run_stream()` is long-running. Using `@rx.event(background=True)` keeps it off the Reflex event loop. State updates are pushed atomically via `async with self:` blocks.

### Settings bridge
Cross-state communication uses a module-level `_shared_config` dict in `rflx/state/settings.py`. `SettingsState.save_agent_settings()` writes config values and sets `chat._agent = None` to force recreation. This avoids Reflex state hierarchy constraints (substates can access parents but not siblings).

### Agent singleton
The PydanticAI agent is created once at module level (`_agent` in `chat.py`) and reused. Tool functions are registered at creation time. The agent is recreated when settings change.

## Deferred Work

- **Core Package extraction** — The shared engine files are currently copied between docl and rflx. A future step is to extract them into a local package that both projects depend on.
- **Markdown chunking** — `.md` files skip Docling and fall back to SimpleChunker (paragraph splitting). Structure-aware markdown chunking would improve chunk quality.
- **Admin/user segregation** — Admin tools (ingestion config, chunk inspector, agent settings) are currently mixed with user-facing pages. A planned refactor moves admin features under an `/admin/` route prefix.
