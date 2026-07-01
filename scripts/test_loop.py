"""Echo-loop test: STT -> TTS.

Usage:
    python scripts/test_loop.py path/to/recording.wav

Takes an audio file, transcribes it to text (STT), then speaks that text back
(TTS) and offers to play it. This proves the full audio pipeline works end to
end. The real assistant will slot the AI brain (Claude) between these two steps:

    audio -> [STT] -> text -> [Claude] -> reply -> [TTS] -> audio

Requirements:
    STT: pip install -r requirements-stt.txt   (or STT_PROVIDER=deepgram)
    TTS: docker compose up -d                  (or TTS_PROVIDER=gtts)
"""

import asyncio
import mimetypes
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.stt.factory import create_stt_provider  # noqa: E402
from app.services.stt.service import STTService  # noqa: E402
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
        print("Usage: python scripts/test_loop.py path/to/recording.wav")
        sys.exit(1)

    audio_path = sys.argv[1]
    if not os.path.isfile(audio_path):
        print(f"File not found: {audio_path}")
        sys.exit(1)

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"

    files = AudioFileManager()
    stt = STTService(create_stt_provider())
    tts = TTSService(create_tts_provider(), files)

    # ── Step 1: STT ──────────────────────────────────────────────────────────
    print(f"[1/2] Transcribing {audio_path} ...")
    try:
        transcript = await stt.transcribe(audio_bytes, mime_type)
    except Exception as exc:  # noqa: BLE001
        print(f"  STT FAILED: {exc}")
        print("  Whisper needs:  pip install -r requirements-stt.txt")
        sys.exit(1)

    print(f"  Heard ({transcript.provider}, conf {transcript.confidence}):")
    print(f"    {transcript.text!r}")

    if not transcript.text.strip():
        print("  Nothing transcribed — is the recording audible speech?")
        sys.exit(1)

    # ── Step 2: TTS ──────────────────────────────────────────────────────────
    print("\n[2/2] Speaking it back ...")
    try:
        spoken = await tts.synthesize(transcript.text)
    except Exception as exc:  # noqa: BLE001
        print(f"  TTS FAILED: {exc}")
        print("  Start Coqui (docker compose up -d) or set TTS_PROVIDER=gtts.")
        sys.exit(1)

    filename = spoken.url.rsplit("/", 1)[-1]
    path = files.path(filename)
    print(f"  Spoken by {spoken.provider}, saved to:\n    {path}")

    answer = input("\nPlay the echo now? [y/N] ").strip().lower()
    if answer == "y":
        _play(str(path))


if __name__ == "__main__":
    asyncio.run(main())
