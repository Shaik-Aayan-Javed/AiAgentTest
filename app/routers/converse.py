"""Full voice-turn endpoint — the one call the browser's push-to-talk button makes.

audio in  →  STT  →  LLM (with history)  →  TTS  →  audio out (URL) + text

The frontend records the mic, POSTs the audio here with the running conversation,
gets back the transcript, the reply text, and a URL to the spoken reply it can
play immediately. Conversation state stays on the client (sent as `history`), so
this endpoint is stateless.
"""

import json

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.llm.base import Message
from app.services.llm.service import get_llm_service
from app.services.stt.service import get_stt_service
from app.services.tts.service import get_tts_service

router = APIRouter(prefix="/converse", tags=["converse"])


class ConverseResponse(BaseModel):
    transcript: str          # what the caller said
    reply: str               # what the AI said
    audio_url: str           # spoken reply, ready to play
    provider: str            # which brain answered (Claude / Gemini)
    model: str
    stt_ms: int
    llm_ms: int
    tts_ms: int


@router.post("", response_model=ConverseResponse, summary="One full voice turn")
async def converse(
    audio: UploadFile = File(...),
    history: str = Form("[]"),
) -> ConverseResponse:
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="No audio uploaded")

    # 1. Speech → text
    try:
        transcript = await get_stt_service().transcribe(
            audio_bytes, audio.content_type or "audio/webm"
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    if not transcript.text.strip():
        raise HTTPException(status_code=422, detail="No speech detected in the audio")

    # 2. Build the conversation and ask the brain
    try:
        prior = json.loads(history) if history else []
        messages = [Message(role=m["role"], content=m["content"]) for m in prior]
    except (json.JSONDecodeError, KeyError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid history payload")

    messages.append(Message(role="user", content=transcript.text))

    try:
        reply = await get_llm_service().reply(messages)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"LLM request failed: {exc}")

    # 3. Text → speech
    try:
        spoken = await get_tts_service().synthesize(reply.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Speech synthesis failed: {exc}")

    return ConverseResponse(
        transcript=transcript.text,
        reply=reply.text,
        audio_url=spoken.url,
        provider=reply.provider,
        model=reply.model,
        stt_ms=transcript.latency_ms,
        llm_ms=reply.latency_ms,
        tts_ms=spoken.latency_ms,
    )
