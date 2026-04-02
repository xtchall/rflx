"""Documents page — upload, list, and manage documents."""

import reflex as rx

from rflx.state.documents import DocumentInfo, DocumentState, IngestionResultInfo


# ---------------------------------------------------------------------------
# Upload tab
# ---------------------------------------------------------------------------


def _upload_section() -> rx.Component:
    return rx.vstack(
        rx.callout(
            "Supported formats: PDF, DOCX, PPTX, XLSX, HTML, TXT, MD, MP3, WAV, M4A, FLAC. "
            "Audio files will be automatically transcribed.",
            icon="info",
        ),
        # Upload dropzone — stages files without starting ingestion
        rx.upload(
            rx.vstack(
                rx.text("Drag and drop files here or click to select", size="3"),
                rx.text(
                    "Files will be staged for review before ingestion",
                    size="2",
                    color="var(--gray-9)",
                ),
                align="center",
                spacing="1",
            ),
            id="doc_upload",
            on_drop=DocumentState.handle_upload(
                rx.upload_files(upload_id="doc_upload")
            ),
            border="2px dashed var(--gray-7)",
            border_radius="12px",
            padding="40px",
            width="100%",
            multiple=True,
            accept={
                "application/pdf": [".pdf"],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                "text/html": [".html"],
                "text/plain": [".txt"],
                "text/markdown": [".md"],
                "audio/mpeg": [".mp3"],
                "audio/wav": [".wav"],
                "audio/x-m4a": [".m4a"],
                "audio/flac": [".flac"],
            },
            disabled=DocumentState.is_ingesting,
        ),
        # Staged files + start button
        rx.cond(
            DocumentState.staged_files.length() > 0,
            rx.vstack(
                rx.text(
                    DocumentState.staged_files.length().to(str) + " file(s) staged:",
                    weight="bold",
                    size="3",
                ),
                rx.foreach(
                    DocumentState.staged_files,
                    lambda f: rx.text(f, size="2", color="var(--gray-11)"),
                ),
                rx.checkbox(
                    "Clean database before ingestion",
                    checked=DocumentState.clean_before_ingest,
                    on_change=DocumentState.set_clean_before,
                ),
                rx.button(
                    "Start Ingestion",
                    on_click=DocumentState.start_ingestion,
                    disabled=DocumentState.is_ingesting,
                    size="3",
                ),
                spacing="2",
                width="100%",
            ),
            rx.fragment(),
        ),
        # Progress
        rx.cond(
            DocumentState.ingestion_status != "",
            rx.vstack(
                rx.cond(
                    DocumentState.is_ingesting,
                    rx.flex(
                        rx.spinner(size="2"),
                        rx.text(DocumentState.ingestion_status, size="2"),
                        spacing="2",
                        align="center",
                    ),
                    rx.callout(
                        DocumentState.ingestion_status,
                        icon="check",
                        color_scheme="green",
                    ),
                ),
                # Results
                rx.cond(
                    DocumentState.ingestion_results.length() > 0,
                    rx.accordion.root(
                        rx.accordion.item(
                            header="Ingestion details",
                            content=rx.vstack(
                                rx.foreach(
                                    DocumentState.ingestion_results,
                                    _ingestion_result_row,
                                ),
                                spacing="1",
                            ),
                        ),
                        type="single",
                        collapsible=True,
                        variant="ghost",
                        width="100%",
                    ),
                    rx.fragment(),
                ),
                width="100%",
                spacing="2",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="4",
    )


def _ingestion_result_row(r: IngestionResultInfo) -> rx.Component:
    return rx.hstack(
        rx.cond(
            r.errors.length() == 0,
            rx.icon("circle_check", color="var(--green-9)", size=14),
            rx.icon("circle_x", color="var(--red-9)", size=14),
        ),
        rx.text(
            r.title,
            " — ",
            r.chunks_created.to(str),
            " chunks",
            size="2",
        ),
        spacing="2",
        align="center",
    )


# ---------------------------------------------------------------------------
# Document list tab
# ---------------------------------------------------------------------------


def _document_list() -> rx.Component:
    return rx.vstack(
        rx.cond(
            DocumentState.total_count == 0,
            rx.callout(
                "No documents in the knowledge base yet. Upload some to get started.",
                icon="inbox",
            ),
            rx.vstack(
                rx.text(
                    "Total documents: ",
                    DocumentState.total_count.to(str),
                    weight="bold",
                    size="3",
                ),
                rx.foreach(DocumentState.documents, _document_card),
                # Pagination
                _pagination(),
                width="100%",
                spacing="3",
            ),
        ),
        width="100%",
        spacing="3",
    )


def _document_card(doc: DocumentInfo) -> rx.Component:
    return rx.card(
        rx.flex(
            rx.vstack(
                rx.text(doc.title, weight="bold", size="3"),
                rx.text(doc.source, size="2", color="var(--gray-11)"),
                rx.hstack(
                    rx.badge(doc.chunk_count.to(str) + " chunks", variant="soft"),
                    rx.text(doc.created_at, size="1", color="var(--gray-9)"),
                    spacing="2",
                ),
                spacing="1",
                flex="1",
            ),
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button("Delete", variant="ghost", color_scheme="red", size="2"),
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Delete Document"),
                    rx.alert_dialog.description(
                        "This will permanently delete this document and all its chunks.",
                    ),
                    rx.flex(
                        rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                        rx.alert_dialog.action(
                            rx.button(
                                "Delete",
                                color_scheme="red",
                                on_click=DocumentState.delete_document(doc.id),
                            ),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                ),
            ),
            justify="between",
            align="start",
            width="100%",
        ),
        width="100%",
    )


def _pagination() -> rx.Component:
    num_pages = (DocumentState.total_count + DocumentState.docs_per_page - 1) // DocumentState.docs_per_page
    return rx.flex(
        rx.button(
            "Previous",
            variant="ghost",
            size="2",
            on_click=DocumentState.prev_page,
            disabled=DocumentState.current_page == 0,
        ),
        rx.text(
            "Page ",
            (DocumentState.current_page + 1).to(str),
            " of ",
            num_pages.to(str),
            size="2",
            color="var(--gray-11)",
        ),
        rx.button(
            "Next",
            variant="ghost",
            size="2",
            on_click=DocumentState.next_page,
            disabled=(DocumentState.current_page + 1) * DocumentState.docs_per_page >= DocumentState.total_count,
        ),
        justify="between",
        align="center",
        width="100%",
    )


# ---------------------------------------------------------------------------
# Ingestion settings tab
# ---------------------------------------------------------------------------


def _ingestion_settings() -> rx.Component:
    return rx.vstack(
        rx.heading("Ingestion Settings", size="4"),
        rx.grid(
            rx.vstack(
                rx.text("Chunk Size (characters)", size="2", weight="medium"),
                rx.input(
                    value=DocumentState.chunk_size.to(str),
                    on_change=DocumentState.set_chunk_size,
                    type="number",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Max Chunk Size (characters)", size="2", weight="medium"),
                rx.input(
                    value=DocumentState.max_chunk_size.to(str),
                    on_change=DocumentState.set_max_chunk_size,
                    type="number",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Chunk Overlap (characters)", size="2", weight="medium"),
                rx.input(
                    value=DocumentState.chunk_overlap.to(str),
                    on_change=DocumentState.set_chunk_overlap,
                    type="number",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.checkbox(
                    "Use Semantic Chunking (Docling HybridChunker)",
                    checked=DocumentState.use_semantic_chunking,
                    on_change=DocumentState.set_semantic_chunking,
                ),
                spacing="1",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        rx.separator(),
        # Bulk operations
        rx.vstack(
            rx.heading("Bulk Operations", size="4"),
            rx.callout(
                "These operations affect all documents in the database.",
                icon="triangle_alert",
                color_scheme="orange",
            ),
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button("Clear All Documents", color_scheme="red", variant="soft"),
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Clear All Documents"),
                    rx.alert_dialog.description(
                        "This will permanently delete all documents and chunks. This cannot be undone.",
                    ),
                    rx.flex(
                        rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                        rx.alert_dialog.action(
                            rx.button(
                                "Delete Everything",
                                color_scheme="red",
                                on_click=DocumentState.clear_all,
                            ),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def documents_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Documents", size="6"),
        rx.separator(),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Upload", value="upload"),
                rx.tabs.trigger("Document List", value="list"),
                rx.tabs.trigger("Ingestion Settings", value="settings"),
            ),
            rx.tabs.content(_upload_section(), value="upload", padding_top="4"),
            rx.tabs.content(_document_list(), value="list", padding_top="4"),
            rx.tabs.content(_ingestion_settings(), value="settings", padding_top="4"),
            default_value="upload",
            width="100%",
        ),
        width="100%",
        padding="4",
        spacing="3",
    )
