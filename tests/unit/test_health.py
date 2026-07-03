from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.health import ProviderStatus


@pytest.fixture
def client():
    return TestClient(app)


def _healthy(provider: str) -> ProviderStatus:
    return ProviderStatus(status="healthy", provider=provider, latency_ms=10)


def _down(provider: str, msg: str = "down") -> ProviderStatus:
    return ProviderStatus(status="down", provider=provider, message=msg)


def _degraded(provider: str, msg: str = "degraded") -> ProviderStatus:
    return ProviderStatus(status="degraded", provider=provider, message=msg)


# All three provider checks are mocked so the endpoint needs no Docker/keys/network.
@patch("app.routers.health._check_tts", new_callable=AsyncMock)
@patch("app.routers.health._check_stt", new_callable=AsyncMock)
@patch("app.routers.health._check_llm", new_callable=AsyncMock)
def test_health_all_healthy(mock_llm, mock_stt, mock_tts, client):
    mock_tts.return_value = _healthy("Coqui XTTS-v2")
    mock_stt.return_value = _healthy("Whisper (faster-whisper)")
    mock_llm.return_value = _healthy("Claude")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["tts"]["status"] == "healthy"
    assert data["stt"]["status"] == "healthy"
    assert data["llm"]["status"] == "healthy"


@patch("app.routers.health._check_tts", new_callable=AsyncMock)
@patch("app.routers.health._check_stt", new_callable=AsyncMock)
@patch("app.routers.health._check_llm", new_callable=AsyncMock)
def test_health_one_provider_down(mock_llm, mock_stt, mock_tts, client):
    mock_tts.return_value = _healthy("Coqui XTTS-v2")
    mock_stt.return_value = _healthy("Whisper (faster-whisper)")
    mock_llm.return_value = _down("Claude", "ANTHROPIC_API_KEY not set")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "down"


@patch("app.routers.health._check_tts", new_callable=AsyncMock)
@patch("app.routers.health._check_stt", new_callable=AsyncMock)
@patch("app.routers.health._check_llm", new_callable=AsyncMock)
def test_health_degraded_when_no_down(mock_llm, mock_stt, mock_tts, client):
    # degraded + healthy (no "down") → overall degraded, not down
    mock_tts.return_value = _degraded("Coqui XTTS-v2 → gTTS")
    mock_stt.return_value = _healthy("Whisper (faster-whisper)")
    mock_llm.return_value = _healthy("Gemini")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "degraded"


@patch("app.routers.health._check_tts", new_callable=AsyncMock)
@patch("app.routers.health._check_stt", new_callable=AsyncMock)
@patch("app.routers.health._check_llm", new_callable=AsyncMock)
def test_health_response_shape(mock_llm, mock_stt, mock_tts, client):
    mock_tts.return_value = _healthy("Coqui XTTS-v2")
    mock_stt.return_value = _healthy("Whisper (faster-whisper)")
    mock_llm.return_value = _healthy("Claude")
    data = client.get("/api/health").json()
    for key in ("status", "environment", "tts", "stt", "llm"):
        assert key in data
    for section in ("tts", "stt", "llm"):
        assert "provider" in data[section]
        assert "status" in data[section]
