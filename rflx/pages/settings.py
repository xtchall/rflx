"""Settings page — agent config, models, API keys, UI preferences."""

import reflex as rx

from rflx.state.settings import SettingsState


# ---------------------------------------------------------------------------
# Agent settings tab
# ---------------------------------------------------------------------------


def _agent_settings_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("Agent Configuration", size="4"),
        # System prompt
        rx.vstack(
            rx.text("System Prompt", size="2", weight="medium"),
            rx.text_area(
                value=SettingsState.system_prompt,
                on_change=SettingsState.set_system_prompt,
                rows="10",
                width="100%",
            ),
            spacing="1",
            width="100%",
        ),
        # Response settings
        rx.heading("Response Settings", size="4"),
        rx.grid(
            rx.vstack(
                rx.text(
                    "Temperature: ",
                    SettingsState.temperature.to(str),
                    size="2",
                    weight="medium",
                ),
                rx.slider(
                    min=0.0,
                    max=2.0,
                    step=0.1,
                    default_value=[0.7],
                    on_value_commit=SettingsState.set_temperature,
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text("Max Response Tokens", size="2", weight="medium"),
                rx.input(
                    value=SettingsState.max_tokens.to(str),
                    on_change=SettingsState.set_max_tokens,
                    type="number",
                ),
                spacing="1",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        # Search settings
        rx.heading("Search Settings", size="4"),
        rx.grid(
            rx.vstack(
                rx.text("Default Search Limit", size="2", weight="medium"),
                rx.input(
                    value=SettingsState.default_search_limit.to(str),
                    on_change=SettingsState.set_search_limit,
                    type="number",
                ),
                spacing="1",
            ),
            rx.vstack(
                rx.text(
                    "Similarity Threshold: ",
                    SettingsState.similarity_threshold.to(str),
                    size="2",
                    weight="medium",
                ),
                rx.slider(
                    min=0.0,
                    max=1.0,
                    step=0.05,
                    default_value=[0.0],
                    on_value_commit=SettingsState.set_similarity_threshold,
                ),
                spacing="1",
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        # Save / reset
        rx.flex(
            rx.button("Save Agent Settings", on_click=SettingsState.save_agent_settings, size="3"),
            rx.button(
                "Reset to Defaults",
                variant="ghost",
                on_click=SettingsState.reset_agent_settings,
                size="3",
            ),
            spacing="2",
        ),
        width="100%",
        spacing="4",
    )


# ---------------------------------------------------------------------------
# Model configuration tab
# ---------------------------------------------------------------------------


def _model_config_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("Model Configuration", size="4"),
        rx.callout(
            "Model changes require updating environment variables and restarting the app.",
            icon="info",
        ),
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.text("LLM Model", size="2", weight="medium"),
                    rx.code(SettingsState.llm_model, size="3"),
                    spacing="2",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Embedding Model", size="2", weight="medium"),
                    rx.code(SettingsState.embedding_model, size="3"),
                    spacing="2",
                ),
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        rx.accordion.root(
            rx.accordion.item(
                header="Example .env Configuration",
                content=rx.code_block(
                    "# AI Model Configuration\n"
                    "LLM_CHOICE=gpt-4o-mini\n"
                    "EMBEDDING_MODEL=text-embedding-3-small\n\n"
                    "# OpenAI API Key\n"
                    "OPENAI_API_KEY=sk-your-key-here\n\n"
                    "# Database\n"
                    "DATABASE_URL=postgresql://user:password@localhost:5432/docl",
                    language="bash",
                ),
            ),
            type="single",
            collapsible=True,
            variant="ghost",
            width="100%",
        ),
        width="100%",
        spacing="4",
    )


# ---------------------------------------------------------------------------
# API keys tab
# ---------------------------------------------------------------------------


def _api_keys_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("API Key Management", size="4"),
        rx.callout(
            "API keys are loaded from environment variables. Never commit keys to version control.",
            icon="shield",
            color_scheme="orange",
        ),
        rx.grid(
            rx.card(
                rx.vstack(
                    rx.text("OpenAI API Key", size="2", weight="medium"),
                    rx.cond(
                        SettingsState.has_openai_key,
                        rx.vstack(
                            rx.badge("Configured", color_scheme="green"),
                            rx.code(SettingsState.openai_key_preview, size="2"),
                            spacing="1",
                        ),
                        rx.badge("Not Found", color_scheme="red"),
                    ),
                    spacing="2",
                ),
            ),
            rx.card(
                rx.vstack(
                    rx.text("Database URL", size="2", weight="medium"),
                    rx.cond(
                        SettingsState.has_database_url,
                        rx.vstack(
                            rx.badge("Configured", color_scheme="green"),
                            rx.code(SettingsState.db_url_preview, size="2"),
                            spacing="1",
                        ),
                        rx.badge("Not Found", color_scheme="red"),
                    ),
                    spacing="2",
                ),
            ),
            columns="2",
            spacing="4",
            width="100%",
        ),
        rx.separator(),
        rx.button(
            "Test API Connection",
            on_click=SettingsState.test_api_connection,
            variant="soft",
        ),
        rx.cond(
            SettingsState.connection_test_result != "",
            rx.cond(
                SettingsState.connection_test_success,
                rx.callout(SettingsState.connection_test_result, icon="check", color_scheme="green"),
                rx.callout(SettingsState.connection_test_result, icon="circle_x", color_scheme="red"),
            ),
            rx.fragment(),
        ),
        width="100%",
        spacing="4",
    )


# ---------------------------------------------------------------------------
# UI preferences tab
# ---------------------------------------------------------------------------


def _ui_preferences_tab() -> rx.Component:
    return rx.vstack(
        rx.heading("Display Settings", size="4"),
        rx.vstack(
            rx.checkbox(
                "Show Message Timestamps",
                checked=SettingsState.show_timestamps,
                on_change=SettingsState.set_show_timestamps,
            ),
            rx.checkbox(
                "Show Tool Calls by Default",
                checked=SettingsState.show_tool_calls,
                on_change=SettingsState.set_show_tool_calls,
            ),
            rx.checkbox(
                "Show Sources by Default",
                checked=SettingsState.show_sources,
                on_change=SettingsState.set_show_sources,
            ),
            spacing="3",
        ),
        rx.separator(),
        rx.vstack(
            rx.text("Documents per Page", size="2", weight="medium"),
            rx.select(
                ["10", "25", "50", "100"],
                value=SettingsState.documents_per_page.to(str),
                on_change=SettingsState.set_documents_per_page,
            ),
            spacing="1",
        ),
        rx.separator(),
        rx.flex(
            rx.button("Save UI Settings", on_click=SettingsState.save_ui_settings, size="3"),
            rx.button(
                "Reset All Settings",
                variant="ghost",
                color_scheme="red",
                on_click=SettingsState.reset_all_settings,
                size="3",
            ),
            spacing="2",
        ),
        width="100%",
        spacing="4",
    )


# ---------------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------------


def settings_page() -> rx.Component:
    return rx.vstack(
        rx.heading("Settings", size="6"),
        rx.separator(),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Agent Settings", value="agent"),
                rx.tabs.trigger("Model Configuration", value="models"),
                rx.tabs.trigger("API Keys", value="api"),
                rx.tabs.trigger("UI Preferences", value="ui"),
            ),
            rx.tabs.content(_agent_settings_tab(), value="agent", padding_top="4"),
            rx.tabs.content(_model_config_tab(), value="models", padding_top="4"),
            rx.tabs.content(_api_keys_tab(), value="api", padding_top="4"),
            rx.tabs.content(_ui_preferences_tab(), value="ui", padding_top="4"),
            default_value="agent",
            width="100%",
        ),
        width="100%",
        padding="4",
        spacing="3",
    )
