"""Voice-sample management — the reference audio Coqui clones from.

The Voice Studio records a WAV in the browser and POSTs it here; we save it to
`assets/voice_sample.wav` (mounted into the Coqui container as the speaker
`voice_sample`). Coqui then synthesises in that voice.
"""

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.config import settings
from app.utils.audio import wav_duration_ms

router = APIRouter(prefix="/voice", tags=["voice"])


class SampleStatus(BaseModel):
    exists: bool
    duration_ms: int | None = None
    bytes: int | None = None


def _sample_path() -> Path:
    return Path(settings.voice_sample_path)


@router.get("/sample", response_model=SampleStatus, summary="Voice sample status")
async def sample_status() -> SampleStatus:
    path = _sample_path()
    if not path.is_file():
        return SampleStatus(exists=False)
    data = path.read_bytes()
    return SampleStatus(exists=True, duration_ms=wav_duration_ms(data), bytes=len(data))


@router.post("/sample", response_model=SampleStatus, summary="Save the voice sample (WAV)")
async def upload_sample(audio: UploadFile = File(...)) -> SampleStatus:
    data = await audio.read()
    if len(data) < 2000:
        raise HTTPException(
            status_code=400,
            detail="Recording too short — record at least a few seconds of clear speech.",
        )
    path = _sample_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return SampleStatus(exists=True, duration_ms=wav_duration_ms(data), bytes=len(data))


@router.get("/sample/audio", summary="Download the saved voice sample")
async def sample_audio() -> FileResponse:
    path = _sample_path()
    if not path.is_file():
        raise HTTPException(status_code=404, detail="No voice sample saved")
    return FileResponse(str(path), media_type="audio/wav", filename="voice_sample.wav")


@router.delete("/sample", summary="Delete the voice sample")
async def delete_sample() -> dict:
    path = _sample_path()
    if path.is_file():
        path.unlink()
    return {"deleted": True}
