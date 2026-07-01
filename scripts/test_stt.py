"""CLI test for the STT module.

Usage:
    python scripts/test_stt.py path/to/recording.wav

Transcribes an audio file and prints the text, confidence, latency, and which
provider handled it.

Whisper (default) needs the opt-in engine:  pip install -r requirements-stt.txt
Or set STT_PROVIDER=deepgram in .env to use Deepgram (needs DEEPGRAM_API_KEY).
"""

import asyncio
import mimetypes
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.stt.factory import create_stt_provider  # noqa: E402
from app.services.stt.service import STTService  # noqa: E402


async def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_stt.py path/to/recording.wav")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.isfile(audio_path):
        print(f"File not found: {audio_path}")
        sys.exit(1)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"

    service = STTService(create_stt_provider())

    print(f"Transcribing: {audio_path}  ({len(audio_bytes)} bytes, {mime_type})")
    try:
        result = await service.transcribe(audio_bytes, mime_type)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  FAILED: {exc}")
        print("  Whisper needs:  pip install -r requirements-stt.txt")
        print("  Or set STT_PROVIDER=deepgram in .env (needs DEEPGRAM_API_KEY).")
        sys.exit(1)

    print("\n  Result")
    print("  ------")
    print(f"  Provider:   {result.provider}")
    print(f"  Language:   {result.language}")
    print(f"  Confidence: {result.confidence}")
    print(f"  Audio:      {result.duration_ms} ms")
    print(f"  Latency:    {result.latency_ms} ms")
    print(f"\n  Transcript:\n  {result.text!r}")


if __name__ == "__main__":
    asyncio.run(main())
