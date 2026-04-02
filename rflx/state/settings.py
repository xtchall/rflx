"""Settings state with shared config bridge for cross-state communication."""

import logging
import os
from typing import Any

import reflex as rx

from utils.providers import get_model_info

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared config — module-level dict readable by other states (e.g., ChatState)
# ---------------------------------------------------------------------------

_shared_config: dict[str, Any] = {}


def get_config(key: str, default: Any = None) -> Any:
    """Read a shared config value."""
    return _shared_config.get(key, default)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


DEFAULT_SYSTEM_PROMPT = """You are an intelligent knowledge assistant with access to a document knowledge base.

Your responsibilities:
1. Always search the knowledge base before answering questions
2. Provide accurate, contextual answers based on the retrieved information
3. Cite your sources explicitly (document titles and sources)
4. If information is not in the knowledge base, say so clearly
5. Ask for clarification if the question is ambiguous
6. Be concise but thorough in your responses

Remember: Always ground your answers in the retrieved documents and cite sources!
"""


class SettingsState(rx.State):
    """Application settings."""

    # Agent settings
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 2000
    default_search_limit: int = 5
    similarity_threshold: float = 0.0

    # Model info (read-only display)
    llm_model: str = ""
    embedding_model: str = ""

    # API key status
    has_openai_key: bool = False
    has_database_url: bool = False
    openai_key_preview: str = ""
    db_url_preview: str = ""

    # Connection test
    connection_test_result: str = ""
    connection_test_success: bool = False

    # UI preferences
    show_timestamps: bool = False
    show_tool_calls: bool = False
    show_sources: bool = True
    documents_per_page: int = 25

    def load_settings(self):
        """Load settings on page load."""
        info = get_model_info()
        self.llm_model = info["llm_model"]
        self.embedding_model = info["embedding_model"]

        # Check API keys
        openai_key = os.getenv("OPENAI_API_KEY", "")
        self.has_openai_key = bool(openai_key)
        if len(openai_key) > 10:
            self.openai_key_preview = f"{openai_key[:7]}...{openai_key[-4:]}"

        db_url = os.getenv("DATABASE_URL", "")
        self.has_database_url = bool(db_url)
        if "@" in db_url:
            parts = db_url.split("@")
            self.db_url_preview = f"{parts[0].split(':')[0]}:***@{parts[1]}"

    def save_agent_settings(self):
        """Save agent settings and invalidate cached agent."""
        _shared_config["system_prompt"] = self.system_prompt
        _shared_config["temperature"] = self.temperature
        _shared_config["max_tokens"] = self.max_tokens
        _shared_config["default_search_limit"] = self.default_search_limit
        _shared_config["similarity_threshold"] = self.similarity_threshold

        # Force agent recreation in ChatState
        import rflx.state.chat as chat_mod

        chat_mod._agent = None

    def reset_agent_settings(self):
        """Reset agent settings to defaults."""
        self.system_prompt = DEFAULT_SYSTEM_PROMPT
        self.temperature = 0.7
        self.max_tokens = 2000
        self.default_search_limit = 5
        self.similarity_threshold = 0.0
        self.save_agent_settings()

    def set_system_prompt(self, val: str):
        self.system_prompt = val

    def set_temperature(self, val: list[float]):
        self.temperature = val[0]

    def set_max_tokens(self, val: str):
        try:
            self.max_tokens = int(val)
        except ValueError:
            pass

    def set_search_limit(self, val: str):
        try:
            self.default_search_limit = int(val)
        except ValueError:
            pass

    def set_similarity_threshold(self, val: list[float]):
        self.similarity_threshold = round(val[0], 2)

    def set_show_timestamps(self, val: bool):
        self.show_timestamps = val

    def set_show_tool_calls(self, val: bool):
        self.show_tool_calls = val

    def set_show_sources(self, val: bool):
        self.show_sources = val

    def set_documents_per_page(self, val: str):
        self.documents_per_page = int(val)

    async def test_api_connection(self):
        """Test OpenAI API connection."""
        try:
            from utils.providers import get_embedding_client, get_embedding_model

            client = get_embedding_client()
            model = get_embedding_model()
            response = await client.embeddings.create(input="test", model=model)
            if response.data:
                dim = len(response.data[0].embedding)
                self.connection_test_result = f"Success! Embedding dimension: {dim}"
                self.connection_test_success = True
            else:
                self.connection_test_result = "Failed: empty response"
                self.connection_test_success = False
        except Exception as e:
            self.connection_test_result = f"Failed: {e}"
            self.connection_test_success = False

    def save_ui_settings(self):
        """Save UI preferences."""
        # Stored in state, persists for the session
        pass

    def reset_all_settings(self):
        """Reset everything to defaults."""
        self.reset_agent_settings()
        self.show_timestamps = False
        self.show_tool_calls = False
        self.show_sources = True
        self.documents_per_page = 25
        self.connection_test_result = ""
