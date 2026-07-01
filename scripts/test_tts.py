"""CLI test for the TTS module.

Usage:
    python scripts/test_tts.py "Hello, how can I help you today?"
    python scripts/test_tts.py "Hello" voice_sample

Synthesises the text, saves the audio file, prints timing details, then offers to
play it. Requires the Coqui container running (docker compose up -d), or set
TTS_PROVIDER=gtts in .env to use the no-Docker fallback.
"""

import asyncio
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.tts.factory import create_tts_provider  # noqa: E402
from app.services.tts.service import TTSService  # noqa: E402
from app.utils.file_manager import AudioFileManager  # noqa: E402


def _play(path: str) -> None:
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(path)  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.run(["afplay", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except Exception as exc:  # noqa: BLE001
        print(f"Could not auto-play ({exc}). Open the file manually:\n  {path}")


async def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/test_tts.py "text to speak" [voice]')
        sys.exit(1)

    text = sys.argv[1]
    voice = sys.argv[2] if len(sys.argv) > 2 else None

    files = AudioFileManager()
    service = TTSService(create_tts_provider(), files)

    print(f"Synthesising: {text!r}")
    try:
        result = await service.synthesize(text, voice)
    except Exception as exc:  # noqa: BLE001
        print(f"\n  FAILED: {exc}")
        print("  Is the Coqui container running?  docker compose up -d")
        print("  Or set TTS_PROVIDER=gtts in .env to use the fallback.")
        sys.exit(1)

    filename = result.url.rsplit("/", 1)[-1]
    path = files.path(filename)

    print("\n  Result")
    print("  ------")
    print(f"  Provider:   {result.provider}")
    print(f"  Processed:  {result.processed_text!r}")
    print(f"  Latency:    {result.latency_ms} ms")
    print(f"  Duration:   {result.duration_ms} ms")
    print(f"  Chars:      {result.character_count}")
    print(f"  Cached:     {result.cached}")
    print(f"  Saved to:   {path}")

    answer = input("\nPlay audio now? [y/N] ").strip().lower()
    if answer == "y":
        _play(str(path))


if __name__ == "__main__":
    asyncio.run(main())
