import asyncio
import time

import httpx
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["health"])


class ProviderStatus(BaseModel):
    status: str          # "healthy" | "degraded" | "down"
    provider: str
    latency_ms: int | None = None
    message: str | None = None


class HealthResponse(BaseModel):
    status: str          # "healthy" | "degraded" | "down"
    environment: str
    tts: ProviderStatus
    stt: ProviderStatus
    llm: ProviderStatus


async def _ping_coqui() -> ProviderStatus:
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.coqui_tts_url}/docs")
        latency = int((time.monotonic() - start) * 1000)
        if resp.status_code == 200:
            return ProviderStatus(
                status="healthy",
                provider="Coqui XTTS-v2",
                latency_ms=latency,
            )
        return ProviderStatus(
            status="degraded",
            provider="Coqui XTTS-v2",
            latency_ms=latency,
            message=f"HTTP {resp.status_code}",
        )
    except httpx.TimeoutException:
        return ProviderStatus(
            status="down",
            provider="Coqui XTTS-v2",
            message="Connection timed out — is Docker running?",
        )
    except httpx.ConnectError:
        return ProviderStatus(
            status="down",
            provider="Coqui XTTS-v2",
            message="Connection refused — run: docker compose up -d",
        )
    except Exception as exc:
        return ProviderStatus(
            status="down",
            provider="Coqui XTTS-v2",
            message=str(exc),
        )


async def _check_stt() -> ProviderStatus:
    """Health of the configured STT provider (Whisper or Deepgram)."""
    from app.services.stt.factory import create_stt_provider

    provider = create_stt_provider()
    start = time.monotonic()
    try:
        ok = await provider.health_check()
        latency = int((time.monotonic() - start) * 1000)
        if ok:
            return ProviderStatus(status="healthy", provider=provider.name, latency_ms=latency)
        if provider.name.startswith("Whisper"):
            message = "faster-whisper not installed — pip install -r requirements-stt.txt"
        else:
            message = "Deepgram unavailable — check DEEPGRAM_API_KEY"
        return ProviderStatus(
            status="down",
            provider=provider.name,
            latency_ms=latency,
            message=message,
        )
    except Exception as exc:
        return ProviderStatus(status="down", provider=provider.name, message=str(exc))


async def _check_llm() -> ProviderStatus:
    """Health of the configured LLM provider (config check only — no live API call)."""
    from app.services.llm.factory import create_llm_provider

    provider = create_llm_provider()
    try:
        ok = await provider.health_check()
        if ok:
            return ProviderStatus(status="healthy", provider=provider.name)
        return ProviderStatus(
            status="down",
            provider=provider.name,
            message=f"{provider.name} API key not set in .env",
        )
    except Exception as exc:
        return ProviderStatus(status="down", provider=provider.name, message=str(exc))


def _overall_status(*providers: ProviderStatus) -> str:
    statuses = {p.status for p in providers}
    if statuses == {"healthy"}:
        return "healthy"
    if "down" in statuses:
        return "down"
    return "degraded"


@router.get("/health", response_model=HealthResponse, summary="Provider health check")
async def health_check() -> HealthResponse:
    tts, stt, llm = await asyncio.gather(_ping_coqui(), _check_stt(), _check_llm())
    return HealthResponse(
        status=_overall_status(tts, stt, llm),
        environment=settings.environment,
        tts=tts,
        stt=stt,
        llm=llm,
    )
