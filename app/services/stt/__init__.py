"""STT package.

Only the (dependency-free) interface is re-exported here so importing the package
does not pull in provider dependencies. Import concrete pieces explicitly:

    from app.services.stt.factory import create_stt_provider
    from app.services.stt.service import get_stt_service, STTService
"""

from app.services.stt.base import STTProvider, TranscriptResult

__all__ = ["STTProvider", "TranscriptResult"]
