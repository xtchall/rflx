"""Home dashboard page."""

import reflex as rx

from rflx.state.home import HomeState


def _stat_card(label: str, value: rx.Var, description: str) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text(label, size="2", color="var(--gray-11)", weight="medium"),
            rx.heading(value, size="7"),
            rx.text(description, size="1", color="var(--gray-9)"),
            spacing="1",
        ),
        width="100%",
    )


def home_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Dashboard", size="6"),
        rx.separator(),
        # Stats row
        rx.grid(
            _stat_card("Documents", HomeState.doc_count.to(str), "Total in knowledge base"),
            _stat_card("Chunks", HomeState.chunk_count.to(str), "Embedded segments"),
            rx.card(
                rx.vstack(
                    rx.text("Database", size="2", color="var(--gray-11)", weight="medium"),
                    rx.cond(
                        HomeState.db_connected,
                        rx.badge("Connected", color_scheme="green", size="2"),
                        rx.badge("Disconnected", color_scheme="red", size="2"),
                    ),
                    rx.text("PostgreSQL + pgvector", size="1", color="var(--gray-9)"),
                    spacing="1",
                ),
                width="100%",
            ),
            rx.card(
                rx.vstack(
                    rx.text("LLM", size="2", color="var(--gray-11)", weight="medium"),
                    rx.code(HomeState.llm_model, size="3"),
                    rx.text(HomeState.embedding_model, size="1", color="var(--gray-9)"),
                    spacing="1",
                ),
                width="100%",
            ),
            columns="4",
            spacing="4",
            width="100%",
        ),
        rx.separator(),
        # Two-column info
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.heading("Quick Start", size="4"),
                    rx.markdown(
                        "1. **Upload Documents** — go to Documents to upload files\n"
                        "2. **Configure Settings** — adjust chunk size and model\n"
                        "3. **Ingest Documents** — process files into the knowledge base\n"
                        "4. **Start Chatting** — ask questions in Chat\n"
                        "5. **Explore Knowledge** — browse in Explorer",
                    ),
                    spacing="3",
                ),
                width="100%",
            ),
            rx.card(
                rx.vstack(
                    rx.heading("Supported Formats", size="4"),
                    rx.markdown(
                        "- **Documents**: PDF, DOCX, PPTX, XLSX, HTML\n"
                        "- **Text**: TXT, MD, Markdown\n"
                        "- **Audio**: MP3, WAV, M4A, FLAC (transcribed)\n\n"
                        "Upload multiple files at once for batch processing.",
                    ),
                    spacing="3",
                ),
                width="100%",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        width="100%",
        padding="4",
        spacing="4",
    )
