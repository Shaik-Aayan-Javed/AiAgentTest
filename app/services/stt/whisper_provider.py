"""Whisper STT — the primary provider (self-hosted, free).

Uses faster-whisper (an optimized Whisper that runs on CPU). The model is loaded
lazily on first use and cached, so importing this module is cheap and the app
starts even if faster-whisper isn't installed yet (it's an opt-in dependency —
see requirements-stt.txt).

This class only knows how to run Whisper. Latency measurement, validation, and
orchestration live in the service layer (high cohesion).
"""

import asyncio
import io
import math

from app.services.stt.base import STTProvider, TranscriptResult


class WhisperSTT(STTProvider):
    name = "Whisper (faster-whisper)"

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
        language: str | None = None,
    ) -> None:
        self._model_size = model_size
        self._device = device
        self._compute_type = compute_type
        self._language = language or None   # "" -> None (auto-detect)
        self._model = None                  # lazy-loaded

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel  # opt-in dependency

            self._model = WhisperModel(
                self._model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
        return self._model

    async def transcribe_file(self, audio_bytes: bytes, mime_type: str) -> TranscriptResult:
        return await asyncio.to_thread(self._transcribe_sync, audio_bytes)

    def _transcribe_sync(self, audio_bytes: bytes) -> TranscriptResult:
        model = self._load_model()
        segments, info = model.transcribe(io.BytesIO(audio_bytes), language=self._language)

        # segments is a generator — consume it once
        collected = list(segments)
        text = " ".join(seg.text.strip() for seg in collected).strip()

        # Approximate a 0–1 confidence from segment average log-probs.
        probs = [math.exp(seg.avg_logprob) for seg in collected if seg.avg_logprob is not None]
        confidence = sum(probs) / len(probs) if probs else 0.0
        confidence = max(0.0, min(1.0, confidence))

        return TranscriptResult(
            text=text,
            confidence=round(confidence, 3),
            duration_ms=int(info.duration * 1000),
            language=info.language,
            provider=self.name,
        )

    async def health_check(self) -> bool:
        try:
            import faster_whisper  # noqa: F401
            return True
        except ImportError:
            return False
