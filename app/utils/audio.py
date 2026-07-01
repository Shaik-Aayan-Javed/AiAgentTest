"""Audio helpers.

Kept deliberately small and dependency-free. Format conversion for Twilio
(mu-law 8kHz) is a later concern and will live here too.
"""

import io
import wave


def wav_duration_ms(audio_bytes: bytes) -> int | None:
    """Return the duration of a WAV clip in milliseconds, or None if not parseable.

    Uses the standard-library `wave` module — no external dependency.
    """
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            if not rate:
                return None
            return int(frames / float(rate) * 1000)
    except (wave.Error, EOFError, OSError):
        return None


def estimate_duration_ms(text: str, chars_per_second: float = 14.0) -> int:
    """Rough spoken-duration estimate when exact parsing isn't available (e.g. MP3).

    ~14 characters per second approximates natural speech at ~150 words/minute.
    """
    return int(len(text) / chars_per_second * 1000)
