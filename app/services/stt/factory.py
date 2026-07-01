"""STT provider factory.

The single place that decides which concrete provider the app uses. Everything
else depends on the `STTProvider` interface, never a concrete class.

Note: unlike TTS, there is no automatic fallback chain — the alternate provider
(Deepgram) needs an API key, so silently falling back to it would fail without
one. Provider selection is explicit via STT_PROVIDER.
"""

from app.config import Settings, settings
from app.services.stt.base import STTProvider
from app.services.stt.deepgram import DeepgramSTT
from app.services.stt.whisper_provider import WhisperSTT


def create_stt_provider(cfg: Settings = settings) -> STTProvider:
    """Build the configured STT provider."""
    provider_name = cfg.stt_provider.lower()

    if provider_name == "deepgram":
        return DeepgramSTT(
            api_key=cfg.deepgram_api_key,
            model=cfg.deepgram_model,
            language=cfg.stt_language or None,
        )

    # default: Whisper (self-hosted)
    return WhisperSTT(
        model_size=cfg.whisper_model_size,
        device=cfg.whisper_device,
        compute_type=cfg.whisper_compute_type,
        language=cfg.stt_language or None,
    )
