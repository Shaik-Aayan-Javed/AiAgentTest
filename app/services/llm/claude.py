"""Claude provider — the reasoning brain (Anthropic SDK).

Uses the async Anthropic client. Default model is Claude Haiku 4.5
(`claude-haiku-4-5`) — the fastest, lowest-cost tier, chosen for real-time voice
latency. Swap to `claude-sonnet-5` or `claude-opus-4-8` via config for complex
cases.

This class only knows how to talk to Claude. Conversation history, system-prompt
management, and latency measurement live in the service layer (high cohesion).

Notes on the request shape (verified against the Anthropic SDK):
- Haiku 4.5 supports `temperature` (the Opus 4.8 / Sonnet 5 tier rejects it).
- Haiku 4.5 does NOT support the `effort` parameter, so it is not sent.
- The API is stateless: the full message history is sent on every call.
"""

from anthropic import AsyncAnthropic

from app.services.llm.base import LLMProvider, LLMResponse, Message


class ClaudeLLM(LLMProvider):
    name = "Claude"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-4-5",
        max_tokens: int = 400,
        temperature: float = 0.7,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        # api_key or None → an empty string would shadow the ANTHROPIC_API_KEY env var
        self._client = AsyncAnthropic(api_key=api_key or None, timeout=timeout)
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def complete(self, system_prompt: str, messages: list[Message]) -> LLMResponse:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": m.role, "content": m.content} for m in messages],
        )

        # response.content is a list of blocks; concatenate the text blocks
        text = "".join(block.text for block in response.content if block.type == "text").strip()

        return LLMResponse(
            text=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self._model,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        # Config check only — deliberately does NOT make a live API call, so polling
        # /health never burns tokens. A live check would cost money on every poll.
        return bool(self._api_key)
