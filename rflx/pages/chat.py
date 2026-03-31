"""Chat page — interactive RAG chat with streaming responses."""

import reflex as rx

from rflx.state.chat import ChatMessage, ChatState


def _message_bubble(msg: ChatMessage) -> rx.Component:
    """Render a single chat message."""
    is_user = msg.role == "user"

    bubble = rx.box(
        rx.markdown(msg.content, size="3"),
        background=rx.cond(is_user, "var(--accent-3)", "var(--gray-3)"),
        padding="12px 16px",
        border_radius="12px",
        max_width="75%",
        align_self=rx.cond(is_user, "flex-end", "flex-start"),
    )

    # Sources accordion (assistant messages only)
    sources_section = rx.cond(
        (~is_user) & (msg.sources.length() > 0),
        rx.accordion.root(
            rx.accordion.item(
                header="Sources",
                content=rx.vstack(
                    rx.foreach(
                        msg.sources,
                        lambda s: rx.text(
                            rx.text.strong(s["title"]),
                            f" — {s['source']}",
                            size="2",
                            color="var(--gray-11)",
                        ),
                    ),
                    spacing="1",
                ),
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="75%",
        ),
        rx.fragment(),
    )

    # Tool calls accordion (assistant messages only)
    tools_section = rx.cond(
        (~is_user) & (msg.tool_calls.length() > 0),
        rx.accordion.root(
            rx.accordion.item(
                header="Tool Calls",
                content=rx.vstack(
                    rx.foreach(
                        msg.tool_calls,
                        lambda tc: rx.code(
                            tc["tool_name"].to(str),
                            size="2",
                        ),
                    ),
                    spacing="1",
                ),
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="75%",
        ),
        rx.fragment(),
    )

    return rx.vstack(
        bubble,
        sources_section,
        tools_section,
        width="100%",
        align_items=rx.cond(is_user, "flex-end", "flex-start"),
        spacing="1",
    )


def _streaming_indicator() -> rx.Component:
    """Show the in-progress response while streaming."""
    return rx.cond(
        ChatState.is_streaming,
        rx.box(
            rx.cond(
                ChatState.current_response != "",
                rx.markdown(ChatState.current_response + " ..."),
                rx.flex(
                    rx.spinner(size="2"),
                    rx.text("Thinking...", size="2", color="var(--gray-11)"),
                    spacing="2",
                    align="center",
                ),
            ),
            background="var(--gray-3)",
            padding="12px 16px",
            border_radius="12px",
            max_width="75%",
            align_self="flex-start",
        ),
        rx.fragment(),
    )


def _chat_input() -> rx.Component:
    """Chat input form."""
    return rx.el.form(
        rx.flex(
            rx.input(
                name="message",
                placeholder="Ask a question about your documents...",
                size="3",
                width="100%",
                disabled=ChatState.is_streaming,
                auto_focus=True,
            ),
            rx.button(
                "Send",
                type="submit",
                size="3",
                disabled=ChatState.is_streaming,
            ),
            spacing="2",
            width="100%",
        ),
        on_submit=ChatState.handle_submit,
        reset_on_submit=True,
        width="100%",
    )


def chat_page() -> rx.Component:
    """The chat page."""
    return rx.vstack(
        # Header
        rx.hstack(
            rx.heading("Chat with Your Knowledge Base", size="6"),
            rx.spacer(),
            rx.button(
                "Clear",
                variant="ghost",
                size="2",
                on_click=ChatState.clear_chat,
            ),
            width="100%",
            align="center",
        ),
        rx.separator(),
        # Messages
        rx.vstack(
            rx.foreach(ChatState.messages, _message_bubble),
            _streaming_indicator(),
            width="100%",
            spacing="3",
            flex="1",
            overflow_y="auto",
            padding_y="4",
        ),
        # Input
        _chat_input(),
        width="100%",
        height="calc(100vh - 4rem)",
        padding="4",
        spacing="3",
    )
