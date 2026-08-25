"""Shared local caches for upstream data (FastF1 HTTP cache, transcripts).

Both are rooted at ``backend/.cache/`` (gitignored) and can be redirected via
``PITWALLEAR_CACHE_DIR``.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

_fastf1_enabled = False
_fastf1_lock = threading.Lock()


def cache_root() -> Path:
    env = os.getenv("PITWALLEAR_CACHE_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent.parent / ".cache"


def ensure_fastf1_cache() -> None:
    """Enable FastF1's on-disk HTTP cache exactly once per process.

    Without this, every analysis re-downloads the same session data twice
    (pace agent + timeline agent).
    """
    global _fastf1_enabled
    if _fastf1_enabled:
        return
    with _fastf1_lock:
        if _fastf1_enabled:
            return
        import fastf1

        path = cache_root() / "fastf1"
        path.mkdir(parents=True, exist_ok=True)
        fastf1.Cache.enable_cache(str(path))
        _fastf1_enabled = True


class TranscriptCache:
    """A tiny JSON-file cache of transcribed radio clips keyed by URL.

    Radio clips are immutable, so their transcripts can be persisted across
    runs — this is what makes repeated analyses of the same race cheap.
    """

    def __init__(self) -> None:
        self._path = cache_root() / "transcripts.json"
        self._lock = threading.Lock()
        self._data: dict[str, str] = {}
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text())
        except Exception:
            self._data = {}

    def get(self, url: str) -> str | None:
        return self._data.get(url)

    def put(self, url: str, text: str) -> None:
        with self._lock:
            self._data[url] = text
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.write_text(json.dumps(self._data))
            except Exception:
                pass  # Cache writes must never break the pipeline.
