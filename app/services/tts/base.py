"""TTS provider contract.

Every text-to-speech implementation (Coqui, gTTS, ElevenLabs later) satisfies
this interface. Nothing outside this package imports a concrete provider — the
factory selects one from config. That is what keeps providers swappable with a
single config change (low coupling).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class AudioResult:
    """Raw synthesis output from a provider (before it is saved to disk)."""

    audio_bytes: bytes
    format: str              # "mp3" | "wav"
    duration_ms: int
    character_count: int
    cached: bool
    provider: str
    voice: str | None = None


class TTSProvider(ABC):
    """Abstract text-to-speech provider."""

    name: str = "unknown"

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> AudioResult:
        """Convert text to speech audio. `voice` overrides the provider default."""

    async def list_voices(self) -> list[str]:
        """Return available voice/speaker names. Override if the provider supports it."""
        return ["default"]

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if the provider is reachable and ready."""
