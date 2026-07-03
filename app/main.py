from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import chat, converse, health, stt, tts, voice


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("app/static/audio").mkdir(parents=True, exist_ok=True)
    yield


if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.environment,
        traces_sample_rate=0.1,
    )

app = FastAPI(
    title="VoiceAI Dashboard API",
    description="AI Voice Assistant — Testing & Training Dashboard",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        settings.server_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount(
    "/audio",
    StaticFiles(directory="app/static/audio"),
    name="audio",
)

app.include_router(health.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(stt.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(converse.router, prefix="/api")
app.include_router(voice.router, prefix="/api")
