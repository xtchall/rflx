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


def _empty_state() -> rx.Component:
    """Show placeholder when no messages exist."""
    return rx.cond(
        ChatState.messages.length() == 0,
        rx.center(
            rx.vstack(
                rx.icon("message_circle", size=32, color="var(--gray-7)"),
                rx.text("Ask anything about your documents", size="3", color="var(--gray-9)"),
                rx.text(
                    "Try: \"What are the key findings?\" or \"Summarize the handbook\"",
                    size="2",
                    color="var(--gray-8)",
                ),
                align="center",
                spacing="2",
            ),
            flex="1",
        ),
        rx.fragment(),
    )


def _streaming_indicator() -> rx.Component:
    """Show the in-progress response while streaming."""
    return rx.cond(
        ChatState.is_streaming,
        rx.box(
            rx.cond(
                ChatState.current_response != "",
                rx.text(ChatState.current_response, size="3", white_space="pre-wrap"),
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
    return rx.flex(
        # Header (fixed)
        rx.hstack(
            rx.heading("Chat with Your Knowledge Base", size="6"),
            rx.spacer(),
            rx.alert_dialog.root(
                rx.alert_dialog.trigger(
                    rx.button("Clear", variant="ghost", size="2"),
                ),
                rx.alert_dialog.content(
                    rx.alert_dialog.title("Clear Chat History"),
                    rx.alert_dialog.description(
                        "This will delete all messages in this conversation.",
                    ),
                    rx.flex(
                        rx.alert_dialog.cancel(rx.button("Cancel", variant="soft")),
                        rx.alert_dialog.action(
                            rx.button(
                                "Clear",
                                color_scheme="red",
                                on_click=ChatState.clear_chat,
                            ),
                        ),
                        spacing="3",
                        justify="end",
                    ),
                ),
            ),
            width="100%",
            align="center",
            flex_shrink="0",
        ),
        rx.separator(flex_shrink="0"),
        # Messages (scrollable region)
        rx.box(
            rx.vstack(
                _empty_state(),
                rx.foreach(ChatState.messages, _message_bubble),
                _streaming_indicator(),
                width="100%",
                spacing="3",
                padding_y="4",
            ),
            flex="1",
            overflow_y="auto",
            width="100%",
            min_height="0",
        ),
        # Input (pinned to bottom)
        _chat_input(),
        direction="column",
        height="100%",
        padding="4",
        gap="3",
        width="100%",
    )
