"""TTS provider factory.

The single place that decides which concrete provider the app uses. Everything
else depends on the `TTSProvider` interface, never on a concrete class — so
swapping Coqui for ElevenLabs later is a one-line change here plus a new module.
"""

from app.config import Settings, settings
from app.services.tts.base import AudioResult, TTSProvider
from app.services.tts.coqui import CoquiTTS
from app.services.tts.gtts_provider import GTTSProvider


class FallbackTTSProvider(TTSProvider):
    """Wraps a primary provider and falls back to a secondary one on failure.

    This is the decorator pattern: it *is* a TTSProvider, so the service layer
    can't tell it apart from a plain provider (low coupling).
    """

    def __init__(self, primary: TTSProvider, fallback: TTSProvider) -> None:
        self._primary = primary
        self._fallback = fallback
        self.name = f"{primary.name} -> {fallback.name}"

    async def synthesize(self, text: str, voice: str | None = None) -> AudioResult:
        try:
            return await self._primary.synthesize(text, voice)
        except Exception:
            return await self._fallback.synthesize(text, voice)

    async def list_voices(self) -> list[str]:
        try:
            return await self._primary.list_voices()
        except Exception:
            return await self._fallback.list_voices()

    async def health_check(self) -> bool:
        return await self._primary.health_check()


def create_tts_provider(cfg: Settings = settings) -> TTSProvider:
    """Build the configured TTS provider (with fallback chain if enabled)."""
    provider_name = cfg.tts_provider.lower()

    if provider_name == "gtts":
        return GTTSProvider(language=cfg.tts_language)

    # default: Coqui primary
    primary = CoquiTTS(
        base_url=cfg.coqui_tts_url,
        default_voice=cfg.tts_default_voice,
        language=cfg.tts_language,
    )

    if cfg.tts_fallback_enabled:
        return FallbackTTSProvider(primary, GTTSProvider(language=cfg.tts_language))
    return primary
