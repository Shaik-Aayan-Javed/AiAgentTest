"""TTS orchestration service.

The provider only knows how to turn text into audio bytes. This service owns the
*use case*: preprocess the text, check the cache, call the provider, persist the
audio, and return a result the API can hand back. High cohesion — one job, done
in one place. The router stays a thin HTTP wrapper over this.
"""

import hashlib
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from app.services.tts.base import TTSProvider
from app.utils import text_processor


@dataclass
class TTSResult:
    url: str
    latency_ms: int
    character_count: int
    cached: bool
    provider: str
    processed_text: str
    duration_ms: int


class _FileStore(Protocol):
    """Minimal surface the service needs from a file manager (keeps it testable)."""

    def save(self, audio_bytes: bytes, fmt: str) -> str: ...
    def exists(self, filename: str) -> bool: ...
    def url(self, filename: str) -> str: ...


class TTSService:
    def __init__(self, provider: TTSProvider, file_manager: _FileStore) -> None:
        self._provider = provider
        self._files = file_manager
        # cache key -> (filename, format, duration_ms, provider)
        self._cache: dict[str, tuple[str, int, str]] = {}

    async def synthesize(self, text: str, voice: str | None = None) -> TTSResult:
        processed = text_processor.process(text)
        if not processed:
            raise ValueError("Text is empty after preprocessing")

        key = self._cache_key(processed, voice)
        cached = self._cache.get(key)
        if cached and self._files.exists(cached[0]):
            filename, duration_ms, provider = cached
            return TTSResult(
                url=self._files.url(filename),
                latency_ms=0,
                character_count=len(processed),
                cached=True,
                provider=provider,
                processed_text=processed,
                duration_ms=duration_ms,
            )

        start = time.monotonic()
        audio = await self._provider.synthesize(processed, voice)
        latency_ms = int((time.monotonic() - start) * 1000)

        filename = self._files.save(audio.audio_bytes, audio.format)
        self._cache[key] = (filename, audio.duration_ms, audio.provider)

        return TTSResult(
            url=self._files.url(filename),
            latency_ms=latency_ms,
            character_count=audio.character_count,
            cached=False,
            provider=audio.provider,
            processed_text=processed,
            duration_ms=audio.duration_ms,
        )

    async def list_voices(self) -> list[str]:
        return await self._provider.list_voices()

    @staticmethod
    def _cache_key(text: str, voice: str | None) -> str:
        return hashlib.sha256(f"{voice or ''}|{text}".encode()).hexdigest()


@lru_cache
def get_tts_service() -> TTSService:
    """Application-wide singleton, built from config. Injected into the router.

    Provider/file-manager imports are local so that importing `TTSService` itself
    pulls in no provider dependencies (httpx, gtts) — keeps the class unit-testable
    in isolation.
    """
    from app.services.tts.factory import create_tts_provider
    from app.utils.file_manager import AudioFileManager

    return TTSService(create_tts_provider(), AudioFileManager())
