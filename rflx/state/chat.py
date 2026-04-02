"""
Chat state — PydanticAI agent with streaming responses.

Uses @rx.event(background=True) so the long-running LLM stream
doesn't block the Reflex event loop. State mutations happen inside
`async with self:` blocks which push updates to the frontend.
"""

import json
import logging
from typing import Any

import reflex as rx
from pydantic import BaseModel
from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    ToolCallPart,
    ToolReturnPart,
)

from utils.db_utils import hybrid_search, initialize_database
from utils.providers import get_embedding_client, get_embedding_model, get_llm_model

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Search tool (module-level, shared by all sessions)
# ---------------------------------------------------------------------------

async def _search_knowledge_base(query: str, limit: int = 5) -> str:
    """Hybrid search (keyword + vector with RRF) over the knowledge base."""
    try:
        client = get_embedding_client()
        embedding_model = get_embedding_model()

        response = await client.embeddings.create(input=query, model=embedding_model)
        query_embedding = response.data[0].embedding
        embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"

        await initialize_database()

        results = await hybrid_search(query, embedding_str, limit)

        if not results:
            return "No relevant information found in the knowledge base."

        formatted = []
        for i, row in enumerate(results, 1):
            formatted.append(
                f"{i}. **{row['title']}** (score: {row['rrf_score']:.4f})\n"
                f"   Source: `{row['source']}`\n"
                f"   Content: {row['content']}\n"
            )
        return "\n".join(formatted)

    except Exception as e:
        return f"Error searching knowledge base: {e}"


# ---------------------------------------------------------------------------
# Lazy agent singleton
# ---------------------------------------------------------------------------

_agent: Agent | None = None

SYSTEM_PROMPT = """You are an intelligent knowledge assistant with access to a document knowledge base.

Your responsibilities:
1. Always search the knowledge base before answering questions
2. Provide accurate, contextual answers based on the retrieved information
3. Cite your sources explicitly (document titles and sources)
4. If information is not in the knowledge base, say so clearly
5. Ask for clarification if the question is ambiguous
6. Be concise but thorough in your responses

Remember: Always ground your answers in the retrieved documents and cite sources!
"""


def _get_agent() -> Agent:
    global _agent
    if _agent is not None:
        return _agent

    from rflx.state.settings import get_config

    system_prompt = get_config("system_prompt", SYSTEM_PROMPT)
    agent = Agent(get_llm_model(), system_prompt=system_prompt)

    @agent.tool
    async def search_kb(ctx, query: str, limit: int = 5) -> str:
        """Search the knowledge base by semantic similarity."""
        return await _search_knowledge_base(query, limit)

    _agent = agent
    return agent


# ---------------------------------------------------------------------------
# Reflex state
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = ""
    content: str = ""
    sources: list[dict[str, str]] = []
    tool_calls: list[dict[str, Any]] = []


class ChatState(rx.State):
    """Chat state with streaming support."""

    messages: list[ChatMessage] = []
    current_response: str = ""
    is_streaming: bool = False

    # Backend-only vars (not sent to frontend)
    _message_history: list = []

    @rx.event(background=True)
    async def handle_submit(self, form_data: dict):
        """Handle chat form submission with streaming."""
        message = form_data.get("message", "").strip()
        if not message:
            return

        # Add user message and start streaming
        async with self:
            self.messages.append(
                ChatMessage(role="user", content=message)
            )
            self.is_streaming = True
            self.current_response = ""

        # Stream the agent response
        try:
            agent = _get_agent()
            message_history = self._message_history

            async with agent.run_stream(
                message, message_history=message_history
            ) as result:
                async for text in result.stream_text(delta=True):
                    async with self:
                        self.current_response += text

                all_messages = result.all_messages()

            # Extract sources and tool calls from the message history
            sources: list[dict[str, str]] = []
            tool_calls: list[dict[str, Any]] = []

            for msg in all_messages:
                if isinstance(msg, ModelResponse):
                    for part in msg.parts:
                        if isinstance(part, ToolCallPart):
                            tool_calls.append(
                                {"tool_name": part.tool_name, "args": part.args}
                            )
                elif isinstance(msg, ModelRequest):
                    for part in msg.parts:
                        if isinstance(part, ToolReturnPart):
                            content = str(part.content)
                            if "Source:" not in content:
                                continue
                            lines = content.split("\n")
                            for line in lines:
                                if "Source:" not in line:
                                    continue
                                source_path = (
                                    line.split("Source:")[1].strip().strip("`")
                                )
                                title = "Unknown"
                                for prev_line in lines:
                                    if "**" in prev_line and "similarity:" in prev_line:
                                        parts = prev_line.split("**")
                                        if len(parts) >= 2:
                                            title = parts[1]
                                        break
                                sources.append(
                                    {"title": title, "source": source_path}
                                )

            # Deduplicate sources
            seen: set[str] = set()
            unique_sources: list[dict[str, str]] = []
            for s in sources:
                if s["source"] not in seen:
                    unique_sources.append(s)
                    seen.add(s["source"])

            async with self:
                self.messages.append(
                    ChatMessage(
                        role="assistant",
                        content=self.current_response,
                        sources=unique_sources,
                        tool_calls=tool_calls,
                    )
                )
                self.current_response = ""
                self.is_streaming = False
                self._message_history = all_messages

        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            async with self:
                self.messages.append(
                    ChatMessage(
                        role="assistant",
                        content=f"Error: {e}",
                    )
                )
                self.current_response = ""
                self.is_streaming = False

    def clear_chat(self):
        """Clear chat history."""
        self.messages = []
        self.current_response = ""
        self._message_history = []
