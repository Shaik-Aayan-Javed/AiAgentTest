"""Coqui XTTS-v2 provider — the primary TTS with voice cloning.

Talks to the `daswer123/xtts-api-server` container defined in docker-compose.yml.
The voice sample mounted at `assets/voice_sample.wav` is exposed to the server as
the speaker named `voice_sample` (the filename without extension).

This class only knows how to talk to Coqui. It does not know about caching, file
storage, or preprocessing — those live in the service layer (high cohesion).

NOTE: the request/response shape follows the xtts-api-server API. If you swap the
image, the endpoint paths below are the only thing to adjust.
"""

import httpx

from app.services.tts.base import AudioResult, TTSProvider
from app.utils.audio import wav_duration_ms

_SYNTHESIZE_ENDPOINT = "/tts_to_audio/"
_SPEAKERS_ENDPOINT = "/speakers_list"
_HEALTH_ENDPOINT = "/docs"


class CoquiTTS(TTSProvider):
    name = "Coqui XTTS-v2"

    def __init__(
        self,
        base_url: str,
        default_voice: str,
        language: str = "en",
        timeout: float = 60.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_voice = default_voice
        self._language = language
        self._timeout = timeout

    async def synthesize(self, text: str, voice: str | None = None) -> AudioResult:
        speaker = voice or self._default_voice
        payload = {
            "text": text,
            "speaker_wav": speaker,
            "language": self._language,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(f"{self._base_url}{_SYNTHESIZE_ENDPOINT}", json=payload)
            resp.raise_for_status()
            audio = resp.content

        return AudioResult(
            audio_bytes=audio,
            format="wav",
            duration_ms=wav_duration_ms(audio) or 0,
            character_count=len(text),
            cached=False,
            provider=self.name,
            voice=speaker,
        )

    async def list_voices(self) -> list[str]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base_url}{_SPEAKERS_ENDPOINT}")
            resp.raise_for_status()
            data = resp.json()
        # server returns a list of speaker names
        return list(data) if isinstance(data, list) else []

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self._base_url}{_HEALTH_ENDPOINT}")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False
