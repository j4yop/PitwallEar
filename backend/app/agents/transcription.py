"""Transcription agent — speech to text via a Hugging Face Whisper model."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.config import settings
from app.schemas import TranscriptionResult


class TranscriptionAgent:
    """Wraps a Hugging Face ASR pipeline with lazy loading and caching.

    The pipeline is loaded in cache-only mode by default so a cold machine
    fails fast with an empty transcript instead of downloading a large model
    inside a request handler. Set ``PITWALLEAR_ALLOW_DOWNLOAD=1`` to fetch
    the model on first use.
    """

    def __init__(self, model_name: str | None = None) -> None:
        self.model_name = model_name or settings.asr_model
        self._pipeline = None
        self._load_failed = False

    @staticmethod
    def _allow_download() -> bool:
        return os.getenv("PITWALLEAR_ALLOW_DOWNLOAD", "0") == "1"

    def _load(self):
        if self._pipeline is None:
            if self._load_failed:
                raise RuntimeError("asr-unavailable: model failed to load earlier")
            try:
                from transformers import pipeline

                # Cache-only by default, mirroring EmotionAgent. Implemented via
                # HF_HUB_OFFLINE rather than pipeline(local_files_only=...) —
                # that kwarg leaks into Whisper's generate() call and raises
                # ValueError on every inference in current transformers versions.
                if not self._allow_download():
                    os.environ.setdefault("HF_HUB_OFFLINE", "1")
                self._pipeline = pipeline(
                    "automatic-speech-recognition",
                    model=self.model_name,
                    token=settings.hf_token or None,
                )
            except Exception as exc:
                self._load_failed = True
                raise RuntimeError(f"asr-unavailable ({type(exc).__name__})") from exc
        return self._pipeline

    def transcribe(self, audio_path: str) -> TranscriptionResult:
        """Transcribe an audio file to text."""
        try:
            asr = self._load()
            # Team radio is English; forcing the language stops multilingual
            # Whisper from misdetecting short noisy clips as silence.
            kwargs = (
                {"generate_kwargs": {"language": "en", "task": "transcribe"}}
                if "whisper" in self.model_name.lower()
                else {}
            )
            result = asr(audio_path, **kwargs)
            text = result.get("text", "").strip()
            return TranscriptionResult(text=text, model=self.model_name)
        except Exception as exc:
            return TranscriptionResult(
                text="",
                # Label the failure so callers can tell it apart from silence.
                model=f"{self.model_name} (asr-unavailable: {type(exc).__name__})",
            )

    def transcribe_bytes(self, audio: bytes) -> TranscriptionResult:
        """Transcribe raw audio bytes by writing them to a temporary file."""
        suffix = Path(getattr(audio, "name", "") or "").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        try:
            return self.transcribe(tmp_path)
        finally:
            os.unlink(tmp_path)
