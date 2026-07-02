"""Fallback LLM provider — a priority chain over two providers.

Depends only on the interface (no config, no SDKs), so it's unit-testable in
isolation. The factory wires the concrete providers into it.
"""

from app.services.llm.base import LLMProvider, LLMResponse, Message


class FallbackLLMProvider(LLMProvider):
    """Tries the primary provider; falls back to the secondary.

    - If the primary has no API key configured, it is skipped entirely.
    - If the primary raises at call time (bad key, rate limit, outage), the
      fallback answers.

    It *is* an LLMProvider (decorator pattern), so callers can't tell it apart
    from a plain provider. `LLMResponse.provider` reveals which one answered.
    """

    def __init__(self, primary: LLMProvider, fallback: LLMProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self.name = f"{primary.name} -> {fallback.name}"

    async def complete(self, system_prompt: str, messages: list[Message]) -> LLMResponse:
        if await self._primary.health_check():
            try:
                return await self._primary.complete(system_prompt, messages)
            except Exception:
                pass  # primary failed at runtime — fall through
        return await self._fallback.complete(system_prompt, messages)

    async def health_check(self) -> bool:
        # Healthy if EITHER provider can answer.
        return await self._primary.health_check() or await self._fallback.health_check()
