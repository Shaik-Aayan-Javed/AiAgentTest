"""LLM provider contract — the reasoning brain.

Every LLM implementation (Claude today; others later) satisfies this interface.
Nothing outside this package imports a concrete provider — the factory selects one
from config, so the brain swaps with a single config change.

Same high-cohesion / low-coupling shape as the STT and TTS packages.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Message:
    """One turn in a conversation."""

    role: str        # "user" | "assistant"
    content: str


@dataclass
class LLMResponse:
    """Raw completion output from a provider (before the service adds latency)."""

    text: str
    input_tokens: int
    output_tokens: int
    model: str
    provider: str


class LLMProvider(ABC):
    """Abstract large-language-model provider."""

    name: str = "unknown"

    @abstractmethod
    async def complete(self, system_prompt: str, messages: list[Message]) -> LLMResponse:
        """Generate a reply given a system prompt and the full conversation history."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is configured and reachable."""
