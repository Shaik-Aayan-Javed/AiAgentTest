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


@patch("app.routers.health._ping_coqui", new_callable=AsyncMock)
@patch("app.routers.health._ping_deepgram", new_callable=AsyncMock)
def test_health_all_healthy(mock_stt, mock_tts, client):
    mock_tts.return_value = _healthy("Coqui XTTS-v2")
    mock_stt.return_value = _healthy("Deepgram")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["tts"]["status"] == "healthy"
    assert data["stt"]["status"] == "healthy"


@patch("app.routers.health._ping_coqui", new_callable=AsyncMock)
@patch("app.routers.health._ping_deepgram", new_callable=AsyncMock)
def test_health_one_provider_down(mock_stt, mock_tts, client):
    mock_tts.return_value = _down("Coqui XTTS-v2", "Connection refused")
    mock_stt.return_value = _healthy("Deepgram")
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "down"
    assert data["tts"]["status"] == "down"


@patch("app.routers.health._ping_coqui", new_callable=AsyncMock)
@patch("app.routers.health._ping_deepgram", new_callable=AsyncMock)
def test_health_response_shape(mock_stt, mock_tts, client):
    mock_tts.return_value = _healthy("Coqui XTTS-v2")
    mock_stt.return_value = _healthy("Deepgram")
    data = client.get("/api/health").json()
    assert "status" in data
    assert "environment" in data
    assert "tts" in data
    assert "stt" in data
    assert "provider" in data["tts"]
    assert "latency_ms" in data["tts"]
