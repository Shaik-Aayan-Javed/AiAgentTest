"""TTS package.

Only the (dependency-free) interface is re-exported here so that importing the
package does not pull in provider dependencies (httpx, gtts, pydantic). Import
concrete pieces from their explicit modules:

    from app.services.tts.factory import create_tts_provider
    from app.services.tts.service import get_tts_service, TTSService
"""

from app.services.tts.base import AudioResult, TTSProvider

__all__ = ["AudioResult", "TTSProvider"]
