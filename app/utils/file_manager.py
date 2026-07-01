"""Temp audio file lifecycle.

Generated audio is written to `app/static/audio/` and served at `/audio/{name}`.
Files accumulate, so `cleanup()` prunes old ones (called on a schedule later, or
manually). This module owns the disk — nothing else writes to that directory.
"""

import time
import uuid
from pathlib import Path

from app.config import settings


class AudioFileManager:
    def __init__(
        self,
        directory: str = "app/static/audio",
        url_prefix: str = "/audio",
    ) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._url_prefix = url_prefix

    def save(self, audio_bytes: bytes, fmt: str) -> str:
        """Write audio bytes to a uniquely-named file; return the filename."""
        filename = f"{uuid.uuid4().hex}.{fmt}"
        (self._dir / filename).write_bytes(audio_bytes)
        return filename

    def exists(self, filename: str) -> bool:
        return (self._dir / filename).is_file()

    def path(self, filename: str) -> Path:
        return self._dir / filename

    def url(self, filename: str) -> str:
        """Full URL the browser/Twilio can fetch (absolute so it works cross-origin)."""
        return f"{settings.server_url}{self._url_prefix}/{filename}"

    def cleanup(self, max_age_seconds: int) -> int:
        """Delete files older than max_age_seconds. Return the count removed."""
        now = time.time()
        removed = 0
        for f in self._dir.glob("*"):
            if f.name == ".gitkeep" or not f.is_file():
                continue
            if now - f.stat().st_mtime > max_age_seconds:
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass
        return removed
