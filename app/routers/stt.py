"""STT HTTP API.

Thin layer over STTService — accepts an uploaded audio file, returns the
transcript. No business logic here.
"""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.services.stt.service import get_stt_service

router = APIRouter(prefix="/stt", tags=["stt"])


class TranscribeResponse(BaseModel):
    text: str
    confidence: float
    duration_ms: int
    latency_ms: int
    language: str
    provider: str


@router.post("/transcribe", response_model=TranscribeResponse, summary="Speech to text")
async def transcribe(file: UploadFile = File(...)) -> TranscribeResponse:
    audio_bytes = await file.read()
    service = get_stt_service()
    try:
        result = await service.transcribe(audio_bytes, file.content_type or "audio/wav")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Transcription failed: {exc}")

    return TranscribeResponse(
        text=result.text,
        confidence=result.confidence,
        duration_ms=result.duration_ms,
        latency_ms=result.latency_ms,
        language=result.language,
        provider=result.provider,
    )
