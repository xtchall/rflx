"""Explorer page — semantic search, document viewer, chunk inspector."""

import reflex as rx

from rflx.state.explorer import (
    ChunkDetail,
    ChunkInfo,
    DocumentDetail,
    ExplorerState,
    SearchResult,
    SimilarChunk,
)


# ---------------------------------------------------------------------------
# Semantic search tab
# ---------------------------------------------------------------------------


def _search_tab() -> rx.Component:
    return rx.vstack(
        rx.el.form(
            rx.flex(
                rx.input(
                    name="query",
                    placeholder="Search your knowledge base...",
                    value=ExplorerState.search_query,
                    on_change=ExplorerState.set_search_query,
                    size="3",
                    width="100%",
                ),
                rx.tooltip(
                    rx.input(
                        value=ExplorerState.search_limit.to(str),
                        on_change=ExplorerState.set_search_limit,
                        type="number",
                        width="80px",
                        size="3",
                        placeholder="10",
                        aria_label="Number of results",
                    ),
                    content="Max results to return",
                ),
                rx.button(
                    "Search",
                    type="submit",
                    size="3",
                    disabled=ExplorerState.is_searching,
                ),
                spacing="2",
                width="100%",
            ),
            on_submit=lambda _: ExplorerState.run_search(),
            width="100%",
        ),
        # Results
        rx.cond(
            ExplorerState.is_searching,
            rx.flex(rx.spinner(size="2"), rx.text("Searching...", size="2"), spacing="2", align="center"),
            rx.fragment(),
        ),
        rx.cond(
            ExplorerState.search_results.length() > 0,
            rx.vstack(
                rx.text(
                    ExplorerState.search_results.length().to(str) + " results",
                    size="2",
                    color="var(--gray-11)",
                ),
                rx.foreach(ExplorerState.search_results, _search_result_card),
                width="100%",
                spacing="2",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="3",
    )


def _similarity_badge(score: rx.Var[float]) -> rx.Component:
    label = score.to(str)
    return rx.cond(
        score >= 0.8,
        rx.badge(label, color_scheme="green", variant="soft"),
        rx.cond(
            score >= 0.6,
            rx.badge(label, color_scheme="yellow", variant="soft"),
            rx.badge(label, color_scheme="red", variant="soft"),
        ),
    )


def _search_result_card(result: SearchResult) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.flex(
                rx.text(result.title, weight="bold", size="3"),
                rx.spacer(),
                _similarity_badge(result.similarity),
                width="100%",
                align="center",
            ),
            rx.text("Source: ", result.source, size="2", color="var(--gray-11)"),
            rx.text("Chunk ", (result.chunk_index + 1).to(str), size="2", color="var(--gray-9)"),
            rx.markdown(result.content),
            rx.flex(
                rx.button(
                    "View Document",
                    variant="ghost",
                    size="2",
                    on_click=ExplorerState.view_document(result.document_id),
                ),
                rx.button(
                    "Inspect Chunk",
                    variant="ghost",
                    size="2",
                    on_click=ExplorerState.inspect_chunk(result.chunk_id),
                ),
                spacing="2",
            ),
            spacing="2",
        ),
        width="100%",
    )


# ---------------------------------------------------------------------------
# Document viewer tab
# ---------------------------------------------------------------------------


def _document_viewer_tab() -> rx.Component:
    return rx.cond(
        ExplorerState.viewing_document,
        _document_detail_view(),
        _recent_documents_list(),
    )


def _recent_documents_list() -> rx.Component:
    return rx.vstack(
        rx.callout("Select a document from search results, or choose from recent documents below.", icon="info"),
        rx.cond(
            ExplorerState.recent_documents.length() > 0,
            rx.vstack(
                rx.foreach(
                    ExplorerState.recent_documents,
                    lambda doc: rx.card(
                        rx.flex(
                            rx.vstack(
                                rx.text(doc["title"].to(str), weight="bold", size="3"),
                                rx.text(
                                    doc["source"].to(str),
                                    " | ",
                                    doc["chunk_count"].to(str),
                                    " chunks",
                                    size="2",
                                    color="var(--gray-11)",
                                ),
                                spacing="1",
                            ),
                            rx.spacer(),
                            rx.button(
                                "View",
                                variant="ghost",
                                size="2",
                                on_click=ExplorerState.view_document(doc["id"].to(str)),
                            ),
                            align="center",
                            width="100%",
                        ),
                        width="100%",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.text("No documents found.", size="2", color="var(--gray-11)"),
        ),
        width="100%",
        spacing="3",
    )


def _breadcrumb(*segments) -> rx.Component:
    """Render a breadcrumb trail from (label, on_click_or_None) pairs."""
    items = []
    for i, (label, action) in enumerate(segments):
        if i > 0:
            items.append(rx.text(" > ", size="2", color="var(--gray-8)"))
        if action is not None:
            items.append(rx.link(label, size="2", on_click=action, color="var(--accent-11)", cursor="pointer"))
        else:
            items.append(rx.text(label, size="2", weight="bold"))
    return rx.flex(*items, align="center", gap="1")


def _document_detail_view() -> rx.Component:
    doc = ExplorerState.document_detail
    return rx.vstack(
        _breadcrumb(
            ("Documents", ExplorerState.back_from_document),
            (doc.title, None),
        ),
        rx.text("Source: ", doc.source, size="2", color="var(--gray-11)"),
        rx.hstack(
            rx.badge(doc.chunks.length().to(str) + " chunks", variant="soft"),
            rx.text(doc.created_at, size="1", color="var(--gray-9)"),
            spacing="2",
        ),
        rx.separator(),
        rx.accordion.root(
            rx.accordion.item(
                header="Full Content",
                content=rx.markdown(doc.content),
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
        rx.heading("Chunks", size="4"),
        rx.accordion.root(
            rx.foreach(doc.chunks, _chunk_accordion_item),
            type="multiple",
            collapsible=True,
            variant="surface",
            width="100%",
        ),
        width="100%",
        spacing="3",
    )


def _chunk_accordion_item(chunk: ChunkInfo) -> rx.Component:
    label = "Chunk " + (chunk.chunk_index + 1).to(str)
    return rx.accordion.item(
        header=label,
        content=rx.vstack(
            rx.markdown(chunk.content),
            rx.cond(
                chunk.token_count,
                rx.text("Tokens: ", chunk.token_count.to(str), size="1", color="var(--gray-9)"),
                rx.fragment(),
            ),
            spacing="2",
        ),
    )


# ---------------------------------------------------------------------------
# Chunk inspector tab
# ---------------------------------------------------------------------------


def _chunk_inspector_tab() -> rx.Component:
    return rx.cond(
        ExplorerState.viewing_chunk,
        _chunk_detail_view(),
        _recent_chunks_list(),
    )


def _recent_chunks_list() -> rx.Component:
    return rx.vstack(
        rx.callout("Select a chunk from search results, or choose from recent chunks below.", icon="info"),
        rx.cond(
            ExplorerState.recent_chunks.length() > 0,
            rx.vstack(
                rx.foreach(
                    ExplorerState.recent_chunks,
                    lambda c: rx.card(
                        rx.flex(
                            rx.vstack(
                                rx.text(
                                    c["title"].to(str),
                                    " — Chunk ",
                                    (c["chunk_index"].to(int) + 1).to(str),
                                    weight="bold",
                                    size="2",
                                ),
                                rx.text(
                                    c["content"].to(str)[:200],
                                    size="2",
                                    color="var(--gray-11)",
                                ),
                                spacing="1",
                            ),
                            rx.spacer(),
                            rx.button(
                                "Inspect",
                                variant="ghost",
                                size="2",
                                on_click=ExplorerState.inspect_chunk(c["id"].to(str)),
                            ),
                            align="start",
                            width="100%",
                        ),
                        width="100%",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.text("No chunks found.", size="2", color="var(--gray-11)"),
        ),
        width="100%",
        spacing="3",
    )


def _chunk_detail_view() -> rx.Component:
    c = ExplorerState.chunk_detail
    return rx.vstack(
        _breadcrumb(
            ("Chunks", ExplorerState.back_from_chunk),
            (c.title, ExplorerState.view_document(c.document_id)),
            ("Chunk " + (c.chunk_index + 1).to(str), None),
        ),
        rx.text("Source: ", c.source, size="2", color="var(--gray-11)"),
        rx.separator(),
        rx.heading("Content", size="4"),
        rx.markdown(c.content),
        rx.separator(),
        # Stats
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.text("Token Count", size="2", color="var(--gray-11)"),
                    rx.heading(c.token_count.to(str), size="5"),
                    spacing="1",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Content Length", size="2", color="var(--gray-11)"),
                    rx.heading(c.content.length().to(str), size="5"),
                    spacing="1",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Embedding Dims", size="2", color="var(--gray-11)"),
                    rx.heading(c.embedding_dim.to(str), size="5"),
                    spacing="1",
                ),
            ),
            columns="3",
            spacing="3",
            width="100%",
        ),
        # Find similar
        rx.separator(),
        rx.heading("Similar Chunks", size="4"),
        rx.button(
            "Find Similar Chunks",
            on_click=ExplorerState.find_similar,
            disabled=ExplorerState.is_finding_similar,
            variant="soft",
        ),
        rx.cond(
            ExplorerState.is_finding_similar,
            rx.flex(rx.spinner(size="2"), rx.text("Searching...", size="2"), spacing="2", align="center"),
            rx.fragment(),
        ),
        rx.cond(
            ExplorerState.similar_chunks.length() > 0,
            rx.vstack(
                rx.foreach(ExplorerState.similar_chunks, _similar_chunk_card),
                spacing="2",
                width="100%",
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="3",
    )


def _similar_chunk_card(sc: SimilarChunk) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.flex(
                rx.text(sc.title, weight="bold", size="2"),
                rx.spacer(),
                _similarity_badge(sc.similarity),
                width="100%",
                align="center",
            ),
            rx.text(sc.content, size="2", color="var(--gray-11)"),
            rx.text("Source: ", sc.source, size="1", color="var(--gray-9)"),
            spacing="1",
        ),
        width="100%",
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def explorer_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Explorer", size="6"),
        rx.separator(),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Semantic Search", value="search"),
                rx.tabs.trigger("Document Viewer", value="documents"),
                rx.tabs.trigger("Chunk Inspector", value="chunks"),
            ),
            rx.tabs.content(_search_tab(), value="search", padding_top="4"),
            rx.tabs.content(_document_viewer_tab(), value="documents", padding_top="4"),
            rx.tabs.content(_chunk_inspector_tab(), value="chunks", padding_top="4"),
            value=ExplorerState.active_tab,
            on_change=ExplorerState.set_active_tab,
            width="100%",
        ),
        width="100%",
        padding="4",
        spacing="3",
    )
