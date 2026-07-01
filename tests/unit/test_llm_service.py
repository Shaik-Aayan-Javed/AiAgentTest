"""Unit tests for LLMService and Conversation.

Uses a fake provider — no Anthropic SDK, no network, no tokens spent. Verifies the
service's own logic: system prompt forwarding, input validation, latency, and
conversation accumulation.
"""

import pytest

from app.services.llm.base import LLMProvider, LLMResponse, Message
from app.services.llm.service import Conversation, LLMService


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self) -> None:
        self.last_system: str | None = None
        self.last_messages: list[Message] | None = None

    async def complete(self, system_prompt: str, messages: list[Message]) -> LLMResponse:
        self.last_system = system_prompt
        self.last_messages = messages
        return LLMResponse(
            text="Hello, how can I help?",
            input_tokens=12,
            output_tokens=6,
            model="fake-model",
            provider=self.name,
        )

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_reply_returns_text_and_tokens():
    service = LLMService(FakeProvider(), "You are helpful.")
    reply = await service.reply([Message("user", "hi")])
    assert reply.text == "Hello, how can I help?"
    assert reply.input_tokens == 12
    assert reply.output_tokens == 6
    assert reply.model == "fake-model"
    assert reply.provider == "fake"


@pytest.mark.asyncio
async def test_system_prompt_is_forwarded():
    provider = FakeProvider()
    service = LLMService(provider, "PERSONA")
    await service.reply([Message("user", "hi")])
    assert provider.last_system == "PERSONA"


@pytest.mark.asyncio
async def test_empty_messages_raises():
    service = LLMService(FakeProvider(), "sys")
    with pytest.raises(ValueError):
        await service.reply([])


@pytest.mark.asyncio
async def test_latency_measured():
    service = LLMService(FakeProvider(), "sys")
    reply = await service.reply([Message("user", "hi")])
    assert reply.latency_ms >= 0


@pytest.mark.asyncio
async def test_full_history_is_sent():
    provider = FakeProvider()
    service = LLMService(provider, "sys")
    history = [
        Message("user", "one"),
        Message("assistant", "two"),
        Message("user", "three"),
    ]
    await service.reply(history)
    assert provider.last_messages is not None
    assert len(provider.last_messages) == 3


def test_conversation_accumulates_turns():
    conversation = Conversation()
    conversation.add_user("hi")
    conversation.add_assistant("hello")
    conversation.add_user("bye")
    roles = [m.role for m in conversation.messages]
    assert roles == ["user", "assistant", "user"]
    assert conversation.messages[0].content == "hi"
