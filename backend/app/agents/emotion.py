"""Emotion agent — reads the driver's tone from audio and/or text.

Two model paths are supported:

* **Audio** — a speech-emotion model (SUPERB benchmark) classifies raw audio
  into eight standard emotion labels, mapped onto the three moods the problem
  statement asks for.
* **Text** — a text-emotion classifier (Twitter-RoBERTa) classifies the
  transcript when no audio is available, or as a cross-check against the audio
  result.

By default models are loaded in ``local_files_only`` mode, so a cold machine
returns a clearly-labelled keyword fallback instead of hanging on a download.
Set ``PITWALLEAR_ALLOW_DOWNLOAD=1`` to let transformers fetch models on first
use (needed for the real audio/text model paths).
"""

from __future__ import annotations

import os
import tempfile

from app.config import settings
from app.schemas import EmotionResult, Mood

# The SUPERB speech-emotion model uses these labels.
_AUDIO_LABELS = ["angry", "calm", "disgust", "fearful", "happy", "neutral", "sad", "surprised"]

# Twitter-RoBERTa-base-emotion uses these four labels.
_TEXT_LABELS = ["anger", "joy", "optimism", "sadness"]

_MOOD_BY_AUDIO_LABEL: dict[str, Mood] = {
    "angry": "Stressed",
    "fearful": "Stressed",
    "surprised": "Stressed",
    "disgust": "Tired",
    "sad": "Tired",
    "calm": "Calm",
    "happy": "Calm",
    "neutral": "Neutral",
}

_MOOD_BY_TEXT_LABEL: dict[str, Mood] = {
    "anger": "Stressed",
    "sadness": "Tired",
    "joy": "Calm",
    "optimism": "Calm",
}

_STRESS_WORDS = {
    "struggling", "terrible", "undriveable", "awful", "stressed",
    "angry", "furious", "hate", "cannot", "can't", "worst", "lost",
    "grip", "gone", "box", "stop", "problem", "damage", "broken",
}
_TIRED_WORDS = {
    "tired", "exhausted", "drained", "sleepy", "fatigue", "knackered",
    "dead", "heavy",
}
_CALM_WORDS = {
    "fine", "good", "okay", "ok", "calm", "happy", "great", "nice",
    "understood", "copy", "clear", "steady",
}


class EmotionAgent:
    """Classifies driver mood from raw audio and/or transcript text."""

    def __init__(self, audio_model: str | None = None, text_model: str | None = None) -> None:
        self.audio_model = audio_model or settings.emotion_model
        self.text_model = text_model or settings.text_emotion_model
        self._audio_classifier = None
        self._text_classifier = None
        self._audio_load_failed = False
        self._text_load_failed = False

    @staticmethod
    def _allow_download() -> bool:
        return os.getenv("PITWALLEAR_ALLOW_DOWNLOAD", "0") == "1"

    def _load_audio(self):
        if self._audio_classifier is None and not self._audio_load_failed:
            from transformers import pipeline

            try:
                self._audio_classifier = pipeline(
                    "audio-classification",
                    model=self.audio_model,
                    token=settings.hf_token or None,
                    # Cache-only by default so a cold machine fails fast rather than
                    # downloading hundreds of MB inside a request handler.
                    local_files_only=not self._allow_download(),
                )
            except Exception:
                self._audio_load_failed = True
        if self._audio_load_failed:
            raise RuntimeError("audio emotion model unavailable")
        return self._audio_classifier

    def _load_text(self):
        if self._text_classifier is None and not self._text_load_failed:
            from transformers import pipeline

            try:
                self._text_classifier = pipeline(
                    "text-classification",
                    model=self.text_model,
                    token=settings.hf_token or None,
                    top_k=None,
                    local_files_only=not self._allow_download(),
                )
            except Exception:
                self._text_load_failed = True
        if self._text_load_failed:
            raise RuntimeError("text emotion model unavailable")
        return self._text_classifier

    def classify_audio(self, audio_path: str) -> EmotionResult:
        """Classify the mood of an audio file."""
        try:
            classifier = self._load_audio()
            predictions = classifier(audio_path)
            top = predictions[0]
            raw_label = top.get("label", "neutral").lower()
            confidence = float(top.get("score", 0.0))
            mood = self._audio_to_mood(raw_label)
            reasoning = self._audio_reasoning(raw_label, confidence)
            return EmotionResult(
                mood=mood,
                confidence=confidence,
                model=self.audio_model,
                reasoning=reasoning,
            )
        except Exception as exc:
            return EmotionResult(
                mood="Neutral",
                confidence=0.0,
                model=self.audio_model,
                reasoning=f"Audio emotion unavailable ({type(exc).__name__}).",
            )

    def classify_bytes(self, audio: bytes) -> EmotionResult:
        """Classify raw audio bytes."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio)
            tmp_path = tmp.name
        try:
            return self.classify_audio(tmp_path)
        finally:
            os.unlink(tmp_path)

    def classify_text(self, text: str) -> EmotionResult:
        """Classify mood from transcript text (no audio)."""
        if not text.strip():
            return EmotionResult(
                mood="Neutral",
                confidence=0.0,
                model=self.text_model,
                reasoning="No transcript text to classify.",
            )

        try:
            classifier = self._load_text()
            predictions = classifier(text)
            # The pipeline returns either a flat list or a list-of-lists; the
            # latter happens with top_k=None on some model cards.
            if predictions and isinstance(predictions[0], list):
                predictions = predictions[0]
            if isinstance(predictions, dict):
                predictions = [predictions]
            top = max(predictions, key=lambda p: p.get("score", 0.0))
            raw_label = top.get("label", "").lower()
            confidence = float(top.get("score", 0.0))
            mood = self._text_to_mood(raw_label)
            reasoning = self._text_reasoning(raw_label, confidence)
            return EmotionResult(
                mood=mood,
                confidence=confidence,
                model=self.text_model,
                reasoning=reasoning,
            )
        except Exception as exc:
            mood, confidence, reasoning = self._keyword_fallback(text)
            reasoning += f" (model unavailable: {type(exc).__name__})"
            return EmotionResult(
                mood=mood,
                confidence=confidence,
                model="keyword-fallback",
                reasoning=reasoning,
            )

    @staticmethod
    def _keyword_fallback(text: str) -> tuple[Mood, float, str]:
        """Deterministic mood from keyword counts, clearly labelled as fallback."""
        lowered = text.lower()
        words = set(lowered.replace(",", " ").replace(".", " ").replace("!", " ").split())
        stressed = len(words & _STRESS_WORDS)
        tired = len(words & _TIRED_WORDS)
        calm = len(words & _CALM_WORDS)

        if stressed >= tired and stressed >= calm and stressed > 0:
            return "Stressed", 0.6, f"Keyword fallback: {stressed} stress signal(s)."
        if tired > stressed and tired >= calm:
            return "Tired", 0.6, f"Keyword fallback: {tired} fatigue signal(s)."
        if calm > 0:
            return "Calm", 0.6, f"Keyword fallback: {calm} calm signal(s)."
        return "Neutral", 0.4, "Keyword fallback: no strong signal found."

    @staticmethod
    def _audio_to_mood(raw_label: str) -> Mood:
        return _MOOD_BY_AUDIO_LABEL.get(raw_label, "Neutral")

    @staticmethod
    def _text_to_mood(raw_label: str) -> Mood:
        return _MOOD_BY_TEXT_LABEL.get(raw_label, "Neutral")

    @staticmethod
    def _audio_reasoning(raw_label: str, confidence: float) -> str:
        if confidence < 0.5:
            return "Low-confidence tone reading; treat as indicative only."
        return f"Dominant tone label '{raw_label}' detected at {confidence:.0%} confidence."

    @staticmethod
    def _text_reasoning(raw_label: str, confidence: float) -> str:
        if confidence < 0.5:
            return "Low-confidence text reading; treat as indicative only."
        return f"Dominant transcript emotion '{raw_label}' at {confidence:.0%} confidence."
