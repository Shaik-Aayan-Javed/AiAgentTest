"""Test the reasoning brain — text REPL or full voice pipeline.

Two modes:

    python scripts/test_conversation.py
        Text REPL — type messages, Claude replies, multi-turn. Type 'quit' to exit.
        Needs only ANTHROPIC_API_KEY in .env.

    python scripts/test_conversation.py my_recording.mp3
        Full voice pipeline — audio -> STT -> Claude -> TTS -> playback.
        Needs STT (Whisper/Deepgram) and TTS (Coqui/gTTS) configured too.

This is the real assistant loop: it *answers* instead of echoing.
"""

import asyncio
import mimetypes
import os
import platform
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402
from app.services.llm.factory import create_llm_provider  # noqa: E402
from app.services.llm.service import Conversation, LLMService  # noqa: E402


def _fmt(reply) -> str:
    return (
        f"  [{reply.provider}/{reply.model} · "
        f"{reply.input_tokens}+{reply.output_tokens} tok · {reply.latency_ms} ms]"
    )


async def _text_repl(service: LLMService) -> None:
    conversation = Conversation()
    print("Text chat with the assistant. Type 'quit' or 'exit' to stop.\n")
    while True:
        try:
            user_text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not user_text:
            continue
        if user_text.lower() in ("quit", "exit"):
            break

        conversation.add_user(user_text)
        try:
            reply = await service.reply(conversation.messages)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
            print("  Is ANTHROPIC_API_KEY set in .env?")
            continue
        conversation.add_assistant(reply.text)
        print(f"AI:  {reply.text}")
        print(_fmt(reply) + "\n")


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
        print(f"Could not auto-play ({exc}). Open manually:\n  {path}")


async def _voice_pipeline(service: LLMService, audio_path: str) -> None:
    # Imported here so the text REPL doesn't require STT/TTS deps installed.
    from app.services.stt.factory import create_stt_provider
    from app.services.stt.service import STTService
    from app.services.tts.factory import create_tts_provider
    from app.services.tts.service import TTSService
    from app.utils.file_manager import AudioFileManager

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    mime_type = mimetypes.guess_type(audio_path)[0] or "audio/wav"

    stt = STTService(create_stt_provider())
    files = AudioFileManager()
    tts = TTSService(create_tts_provider(), files)
    conversation = Conversation()

    print(f"[1/3] Transcribing {audio_path} ...")
    transcript = await stt.transcribe(audio_bytes, mime_type)
    print(f"  Caller said: {transcript.text!r}")
    if not transcript.text.strip():
        print("  Nothing transcribed — is the recording audible speech?")
        return

    print("\n[2/3] Thinking ...")
    conversation.add_user(transcript.text)
    reply = await service.reply(conversation.messages)
    conversation.add_assistant(reply.text)
    print(f"  AI reply: {reply.text!r}")
    print(_fmt(reply))

    print("\n[3/3] Speaking the reply ...")
    spoken = await tts.synthesize(reply.text)
    filename = spoken.url.rsplit("/", 1)[-1]
    path = files.path(filename)
    print(f"  Spoken by {spoken.provider}, saved to:\n    {path}")

    answer = input("\nPlay the reply now? [y/N] ").strip().lower()
    if answer == "y":
        _play(str(path))


async def main() -> None:
    service = LLMService(create_llm_provider(), settings.llm_system_prompt)

    if len(sys.argv) > 1:
        audio_path = sys.argv[1]
        if not os.path.isfile(audio_path):
            print(f"File not found: {audio_path}")
            sys.exit(1)
        try:
            await _voice_pipeline(service, audio_path)
        except Exception as exc:  # noqa: BLE001
            print(f"\n  FAILED: {exc}")
            sys.exit(1)
    else:
        await _text_repl(service)


if __name__ == "__main__":
    asyncio.run(main())
