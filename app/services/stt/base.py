"""STT provider contract.

Every speech-to-text implementation (Whisper, Deepgram, …) satisfies this
interface. Nothing outside this package imports a concrete provider — the factory
selects one from config, so providers swap with a single config change.

Mirrors the TTS package structure deliberately: same shape, same rules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class TranscriptResult:
    """Raw transcription output from a provider (before the service adds latency)."""

    text: str
    confidence: float        # 0.0–1.0
    duration_ms: int         # length of the input audio
    language: str
    provider: str


class STTProvider(ABC):
    """Abstract speech-to-text provider."""

    name: str = "unknown"

    @abstractmethod
    async def transcribe_file(self, audio_bytes: bytes, mime_type: str) -> TranscriptResult:
        """Transcribe a complete audio clip (WAV/MP3/etc.) to text."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is installed/reachable and ready."""
