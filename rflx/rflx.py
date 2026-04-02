"""Reflex app — RAG Knowledge Base frontend."""

import reflex as rx

from rflx.pages.chat import chat_page
from rflx.pages.documents import documents_page
from rflx.pages.explorer import explorer_page
from rflx.pages.home import home_page
from rflx.pages.settings import settings_page
from rflx.state.documents import DocumentState
from rflx.state.explorer import ExplorerState
from rflx.state.home import HomeState
from rflx.state.settings import SettingsState


def _nav_link(text: str, href: str, icon: str) -> rx.Component:
    is_active = rx.State.router.page.path == href
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=16),
            rx.text(text),
            spacing="2",
            align="center",
        ),
        href=href,
        size="3",
        underline="none",
        weight=rx.cond(is_active, "bold", "regular"),
        color=rx.cond(is_active, "var(--accent-11)", "inherit"),
        background=rx.cond(is_active, "var(--accent-3)", "transparent"),
        padding="6px 8px",
        border_radius="var(--radius-2)",
        width="100%",
        display="block",
    )


def layout(page: rx.Component) -> rx.Component:
    """Shared layout with navigation sidebar."""
    return rx.flex(
        # Sidebar
        rx.box(
            rx.vstack(
                rx.heading("docl", size="5", weight="bold"),
                rx.separator(),
                _nav_link("Home", "/", "home"),
                _nav_link("Chat", "/chat", "message_circle"),
                _nav_link("Documents", "/documents", "file_text"),
                _nav_link("Explorer", "/explorer", "search"),
                _nav_link("Settings", "/settings", "settings"),
                spacing="3",
                padding="4",
                height="100%",
            ),
            width="200px",
            min_width="200px",
            border_right="1px solid var(--gray-6)",
            height="100vh",
        ),
        # Main content
        rx.box(
            page,
            flex="1",
            height="100vh",
            overflow_y="auto",
        ),
        width="100%",
        height="100vh",
    )


# ---------------------------------------------------------------------------
# Page wrappers
# ---------------------------------------------------------------------------


def index() -> rx.Component:
    return layout(home_page())


def chat() -> rx.Component:
    return layout(chat_page())


def documents() -> rx.Component:
    return layout(documents_page())


def explorer() -> rx.Component:
    return layout(explorer_page())


def settings() -> rx.Component:
    return layout(settings_page())


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


app = rx.App()
app.add_page(index, route="/", title="Home", on_load=HomeState.load_stats)
app.add_page(chat, route="/chat", title="Chat")
app.add_page(
    documents,
    route="/documents",
    title="Documents",
    on_load=DocumentState.load_documents,
)
app.add_page(
    explorer,
    route="/explorer",
    title="Explorer",
    on_load=[ExplorerState.load_recent_documents, ExplorerState.load_recent_chunks],
)
app.add_page(
    settings,
    route="/settings",
    title="Settings",
    on_load=SettingsState.load_settings,
)
