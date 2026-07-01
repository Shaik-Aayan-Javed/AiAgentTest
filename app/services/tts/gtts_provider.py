"""gTTS provider — the fallback TTS.

Google Translate TTS via the `gtts` library. It cannot clone your voice (generic
voice only) and needs internet, but it has zero setup — no Docker, no model
download. Its role is the safety net: if Coqui is down, callers still hear a
response rather than silence.

gTTS is synchronous, so synthesis runs in a thread to avoid blocking the event
loop.
"""

import asyncio
import io

from app.services.tts.base import AudioResult, TTSProvider
from app.utils.audio import estimate_duration_ms


class GTTSProvider(TTSProvider):
    name = "Google TTS (fallback)"

    def __init__(self, language: str = "en") -> None:
        self._language = language

    async def synthesize(self, text: str, voice: str | None = None) -> AudioResult:
        audio = await asyncio.to_thread(self._synthesize_sync, text)
        return AudioResult(
            audio_bytes=audio,
            format="mp3",
            duration_ms=estimate_duration_ms(text),
            character_count=len(text),
            cached=False,
            provider=self.name,
            voice=None,
        )

    def _synthesize_sync(self, text: str) -> bytes:
        from gtts import gTTS  # imported lazily so the app starts without gtts installed

        buffer = io.BytesIO()
        gTTS(text=text, lang=self._language).write_to_fp(buffer)
        return buffer.getvalue()

    async def health_check(self) -> bool:
        # gTTS has no health endpoint; it depends only on outbound internet.
        return True
