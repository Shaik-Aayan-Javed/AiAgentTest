"""LLM orchestration service + conversation state.

The provider turns (system prompt + history) into a reply. This service owns the
use case: it holds the system prompt (the AI persona), validates input, measures
latency, and returns a reply the API/scripts can use. `Conversation` is a small
in-memory multi-turn holder (Redis-backed per call SID later).
"""

import time
from dataclasses import dataclass, field
from functools import lru_cache

from app.services.llm.base import LLMProvider, Message


@dataclass
class LLMReply:
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str
    latency_ms: int


@dataclass
class Conversation:
    """In-memory conversation history for one session."""

    _messages: list[Message] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self._messages.append(Message("user", text))

    def add_assistant(self, text: str) -> None:
        self._messages.append(Message("assistant", text))

    @property
    def messages(self) -> list[Message]:
        return list(self._messages)


class LLMService:
    def __init__(self, provider: LLMProvider, system_prompt: str) -> None:
        self._provider = provider
        self._system_prompt = system_prompt

    async def reply(self, messages: list[Message]) -> LLMReply:
        if not messages:
            raise ValueError("No messages provided")

        start = time.monotonic()
        result = await self._provider.complete(self._system_prompt, messages)
        latency_ms = int((time.monotonic() - start) * 1000)

        return LLMReply(
            text=result.text,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            model=result.model,
            provider=result.provider,
            latency_ms=latency_ms,
        )


@lru_cache
def get_llm_service() -> LLMService:
    """Application-wide singleton, built from config. Injected into the router.

    Provider/settings imported locally so importing `LLMService` pulls in no
    provider dependencies (anthropic) — keeps the class unit-testable alone.
    """
    from app.config import settings
    from app.services.llm.factory import create_llm_provider

    return LLMService(create_llm_provider(), settings.llm_system_prompt)
