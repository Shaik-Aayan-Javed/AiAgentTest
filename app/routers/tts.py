"""TTS HTTP API.

Thin layer over TTSService — validates input, maps errors to HTTP status codes,
shapes the response. No business logic here.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.tts.service import get_tts_service

router = APIRouter(prefix="/tts", tags=["tts"])


class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    voice: str | None = None


class SynthesizeResponse(BaseModel):
    audio_url: str
    latency_ms: int
    character_count: int
    cached: bool
    provider: str
    processed_text: str
    duration_ms: int


class VoicesResponse(BaseModel):
    voices: list[str]
    default: str


@router.post("/synthesize", response_model=SynthesizeResponse, summary="Text to speech")
async def synthesize(req: SynthesizeRequest) -> SynthesizeResponse:
    service = get_tts_service()
    try:
        result = await service.synthesize(req.text, req.voice)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS synthesis failed: {exc}")

    return SynthesizeResponse(
        audio_url=result.url,
        latency_ms=result.latency_ms,
        character_count=result.character_count,
        cached=result.cached,
        provider=result.provider,
        processed_text=result.processed_text,
        duration_ms=result.duration_ms,
    )


@router.get("/voices", response_model=VoicesResponse, summary="List available voices")
async def voices() -> VoicesResponse:
    service = get_tts_service()
    try:
        available = await service.list_voices()
    except Exception:
        available = []
    return VoicesResponse(voices=available, default=settings.tts_default_voice)
