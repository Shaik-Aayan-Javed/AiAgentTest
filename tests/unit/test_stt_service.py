"""Unit tests for STTService orchestration.

Uses a fake provider — no Whisper model, no Deepgram, no network. Verifies the
service's own logic: input validation, latency measurement, and faithful
pass-through of the provider's result.
"""

import pytest

from app.services.stt.base import STTProvider, TranscriptResult
from app.services.stt.service import STTService


class FakeProvider(STTProvider):
    name = "fake-stt"

    def __init__(self) -> None:
        self.calls = 0

    async def transcribe_file(self, audio_bytes: bytes, mime_type: str) -> TranscriptResult:
        self.calls += 1
        return TranscriptResult(
            text="hello world",
            confidence=0.97,
            duration_ms=1500,
            language="en",
            provider=self.name,
        )

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_transcribe_returns_result():
    service = STTService(FakeProvider())
    result = await service.transcribe(b"RIFFfakeaudio", "audio/wav")
    assert result.text == "hello world"
    assert result.confidence == 0.97
    assert result.duration_ms == 1500
    assert result.provider == "fake-stt"


@pytest.mark.asyncio
async def test_latency_is_measured():
    service = STTService(FakeProvider())
    result = await service.transcribe(b"RIFFfakeaudio", "audio/wav")
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_empty_audio_raises():
    service = STTService(FakeProvider())
    with pytest.raises(ValueError):
        await service.transcribe(b"", "audio/wav")


@pytest.mark.asyncio
async def test_provider_called_once_per_transcription():
    provider = FakeProvider()
    service = STTService(provider)
    await service.transcribe(b"aaa", "audio/wav")
    await service.transcribe(b"bbb", "audio/wav")
    assert provider.calls == 2
