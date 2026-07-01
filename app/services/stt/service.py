"""STT orchestration service.

The provider turns audio into text. This service owns the use case: validate the
input, call the provider, measure latency, and return a result the API can hand
back. The router stays a thin HTTP wrapper over this.
"""

import time
from dataclasses import dataclass
from functools import lru_cache

from app.services.stt.base import STTProvider


@dataclass
class STTResult:
    text: str
    confidence: float
    duration_ms: int      # audio length
    latency_ms: int       # processing time
    language: str
    provider: str


class STTService:
    def __init__(self, provider: STTProvider) -> None:
        self._provider = provider

    async def transcribe(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> STTResult:
        if not audio_bytes:
            raise ValueError("No audio provided")

        start = time.monotonic()
        result = await self._provider.transcribe_file(audio_bytes, mime_type)
        latency_ms = int((time.monotonic() - start) * 1000)

        return STTResult(
            text=result.text,
            confidence=result.confidence,
            duration_ms=result.duration_ms,
            latency_ms=latency_ms,
            language=result.language,
            provider=result.provider,
        )


@lru_cache
def get_stt_service() -> STTService:
    """Application-wide singleton, built from config. Injected into the router.

    Factory imported locally so importing `STTService` pulls in no provider
    dependencies (faster-whisper, httpx) — keeps the class unit-testable alone.
    """
    from app.services.stt.factory import create_stt_provider

    return STTService(create_stt_provider())
