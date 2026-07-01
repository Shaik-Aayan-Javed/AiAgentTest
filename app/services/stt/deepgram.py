"""Deepgram STT — the optional provider.

Kept per the design decision to retain Deepgram as a swappable option. Uses
Deepgram's prerecorded REST endpoint via httpx — no deepgram-sdk dependency
needed, so nothing extra to install; just set DEEPGRAM_API_KEY and
STT_PROVIDER=deepgram.

Works on any Python version (pure API call), which also makes it the reliable
fallback if the local Whisper engine can't be installed.
"""

import httpx

from app.services.stt.base import STTProvider, TranscriptResult

_LISTEN_URL = "https://api.deepgram.com/v1/listen"


class DeepgramSTT(STTProvider):
    name = "Deepgram"

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._language = language or None
        self._timeout = timeout

    async def transcribe_file(self, audio_bytes: bytes, mime_type: str) -> TranscriptResult:
        headers = {
            "Authorization": f"Token {self._api_key}",
            "Content-Type": mime_type or "audio/wav",
        }
        params: dict[str, str] = {"model": self._model, "smart_format": "true"}
        if self._language:
            params["language"] = self._language

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(_LISTEN_URL, headers=headers, params=params, content=audio_bytes)
            resp.raise_for_status()
            data = resp.json()

        alternative = data["results"]["channels"][0]["alternatives"][0]
        return TranscriptResult(
            text=alternative.get("transcript", ""),
            confidence=round(float(alternative.get("confidence", 0.0)), 3),
            duration_ms=int(data.get("metadata", {}).get("duration", 0.0) * 1000),
            language=self._language or "en",
            provider=self.name,
        )

    async def health_check(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {self._api_key}"},
                )
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
