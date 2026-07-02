"""Gemini provider — optional alternative brain (Google Gen AI SDK).

Kept behind the same LLMProvider interface as Claude, so it's a drop-in swap via
`LLM_PROVIDER=gemini`. Claude remains the default.

Uses the `google-genai` SDK (`from google import genai`), imported lazily so the
app runs without it installed unless Gemini is actually selected. `contents` and
`config` are passed as plain dicts (the SDK converts them), which avoids coupling
to specific `types.*` constructor signatures.

NOTE: verify `GEMINI_MODEL` names a model your API key can access — the Gemini
model lineup changes over time; `gemini-2.5-flash` is a reasonable fast/cheap
default (the analog of Claude Haiku).
"""

from app.services.llm.base import LLMProvider, LLMResponse, Message


class GeminiLLM(LLMProvider):
    name = "Gemini"

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        max_tokens: int = 400,
        temperature: float = 0.7,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._client = None  # lazy — created on first use

    def _get_client(self):
        if self._client is None:
            from google import genai  # opt-in dependency (google-genai)

            self._client = genai.Client(api_key=self._api_key or None)
        return self._client

    async def complete(self, system_prompt: str, messages: list[Message]) -> LLMResponse:
        client = self._get_client()

        # Gemini roles are "user" / "model" (not "assistant").
        contents = [
            {
                "role": "model" if m.role == "assistant" else "user",
                "parts": [{"text": m.content}],
            }
            for m in messages
        ]

        response = await client.aio.models.generate_content(
            model=self._model,
            contents=contents,
            config={
                "system_instruction": system_prompt,
                "max_output_tokens": self._max_tokens,
                "temperature": self._temperature,
            },
        )

        text = (response.text or "").strip()
        usage = response.usage_metadata
        return LLMResponse(
            text=text,
            input_tokens=getattr(usage, "prompt_token_count", 0) or 0,
            output_tokens=getattr(usage, "candidates_token_count", 0) or 0,
            model=self._model,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        # Config check only — no live API call, so /health never spends quota.
        return bool(self._api_key)
