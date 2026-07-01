"""Unit tests for TTSService orchestration.

Uses a fake provider and fake file store — no Coqui, no network, no disk. Verifies
the service's own logic: preprocessing is applied, caching avoids re-synthesis,
and empty input is rejected.
"""

import pytest

from app.services.tts.base import AudioResult, TTSProvider
from app.services.tts.service import TTSService


class FakeProvider(TTSProvider):
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    async def synthesize(self, text: str, voice: str | None = None) -> AudioResult:
        self.calls += 1
        return AudioResult(
            audio_bytes=b"RIFFfakeaudio",
            format="wav",
            duration_ms=1000,
            character_count=len(text),
            cached=False,
            provider=self.name,
            voice=voice,
        )

    async def health_check(self) -> bool:
        return True


class FakeFileStore:
    def __init__(self) -> None:
        self._saved: dict[str, bytes] = {}
        self._counter = 0

    def save(self, audio_bytes: bytes, fmt: str) -> str:
        self._counter += 1
        name = f"file{self._counter}.{fmt}"
        self._saved[name] = audio_bytes
        return name

    def exists(self, filename: str) -> bool:
        return filename in self._saved

    def url(self, filename: str) -> str:
        return f"http://test/audio/{filename}"


@pytest.mark.asyncio
async def test_synthesize_returns_result():
    service = TTSService(FakeProvider(), FakeFileStore())
    result = await service.synthesize("Hello world")
    assert result.url.startswith("http://test/audio/")
    assert result.cached is False
    assert result.provider == "fake"
    assert result.duration_ms == 1000


@pytest.mark.asyncio
async def test_cache_hit_skips_provider():
    provider = FakeProvider()
    service = TTSService(provider, FakeFileStore())
    await service.synthesize("Same text")
    second = await service.synthesize("Same text")
    assert second.cached is True
    assert provider.calls == 1  # provider invoked only once


@pytest.mark.asyncio
async def test_different_voices_cache_separately():
    provider = FakeProvider()
    service = TTSService(provider, FakeFileStore())
    await service.synthesize("Hello", voice="a")
    await service.synthesize("Hello", voice="b")
    assert provider.calls == 2


@pytest.mark.asyncio
async def test_markdown_stripped_before_synthesis():
    service = TTSService(FakeProvider(), FakeFileStore())
    result = await service.synthesize("**Bold** text")
    assert result.processed_text == "Bold text"


@pytest.mark.asyncio
async def test_empty_after_processing_raises():
    service = TTSService(FakeProvider(), FakeFileStore())
    with pytest.raises(ValueError):
        await service.synthesize("   ")
