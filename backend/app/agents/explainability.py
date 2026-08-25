"""Explainability and failure/boundary analysis for PitwallEar.

Produces human-inspectable artifacts for every signal and a self-aware list of
failure modes so the co-driver is auditable rather than a black box.
"""

from __future__ import annotations

import os

from app.schemas import (
    AgreementResult,
    CorrelationResult,
    EmotionResult,
    Explainability,
    Mood,
    PaceResult,
    TranscriptionResult,
)


def build_explainability(
    transcription: TranscriptionResult,
    emotion: EmotionResult,
    pace: PaceResult,
    agreement: AgreementResult | None,
    correlation: CorrelationResult | None,
    audio_path: str | None = None,
    text_emotion: EmotionResult | None = None,
) -> Explainability:
    """Assemble the explainability artifact from agent outputs.

    ``text_emotion`` carries the transcript-only reading on the text pipeline
    (where ``emotion`` holds that same text mood); passing it explicitly keeps
    ``text_mood`` populated instead of null.
    """
    prosody: dict = {}
    waveform = False

    if audio_path and os.path.exists(audio_path):
        waveform = True
        prosody = _extract_prosody(audio_path)

    text_mood: Mood | None
    if text_emotion is not None:
        text_mood = text_emotion.mood
    elif agreement is not None:
        text_mood = agreement.text_mood
    else:
        text_mood = None

    return Explainability(
        transcript=transcription.text,
        audio_mood=emotion.mood,
        text_mood=text_mood,
        agreement_reason=agreement.reasoning if agreement else "",
        pace_reason=pace.reasoning,
        causal_reason=correlation.causal.reasoning if correlation and correlation.causal else "",
        waveform_available=waveform,
        prosody_features=prosody,
        failure_modes=_detect_failure_modes(emotion, pace, correlation),
    )


def _extract_prosody(audio_path: str) -> dict:
    """Extract lightweight prosody features if librosa is available."""
    try:
        import librosa

        y, sr = librosa.load(audio_path, sr=16000, mono=True)
        rms = float(librosa.feature.rms(y=y).mean())
        zcr = float(librosa.feature.zero_crossing_rate(y=y).mean())
        pitch, voiced, _ = librosa.pyin(
            y, fmin=50, fmax=600, sr=sr, fill_na=0.0
        )
        voiced_pitch = pitch[voiced] if voiced.any() else pitch
        return {
            "rms_energy": round(rms, 5),
            "zero_crossing_rate": round(zcr, 5),
            "mean_pitch_hz": round(float(voiced_pitch.mean()), 1),
            "duration_s": round(float(len(y) / sr), 2),
        }
    except Exception:
        return {}


def _detect_failure_modes(
    emotion: EmotionResult,
    pace: PaceResult,
    correlation: CorrelationResult | None,
) -> list[str]:
    """Return an honest list of where the current analysis may be unreliable."""
    modes: list[str] = []

    if emotion.model == "keyword-fallback":
        modes.append("Emotion uses keyword fallback (model unavailable or not downloaded).")
    if emotion.model == "audio-unavailable":
        modes.append(
            "Audio tone was NOT read (model unavailable); the mood comes from "
            "the transcript or a neutral default."
        )
    if emotion.confidence > 0 and emotion.calibrated_confidence is not None:
        if emotion.calibrated_confidence < 0.5:
            modes.append("Emotion confidence is low after calibration; treat mood label cautiously.")

    if pace.trend in {"insufficient", "unknown"}:
        modes.append("Pace trend is underdetermined due to too few clean laps.")
    elif not pace.laps:
        modes.append("No lap-time data available; pace and correlation are not computed.")

    if correlation is not None:
        if correlation.sample_size < 10:
            modes.append(
                f"Small sample (n={correlation.sample_size}); causal lead-lag is provisional."
            )
        if correlation.causal is not None and correlation.causal.p_value >= 0.05:
            modes.append("Causal lead-lag result is not statistically significant.")

    # Domain mismatch: general emotion models were not trained on in-car radio.
    if emotion.model in {"superb/wav2vec2-base-superb-er", "keyword-fallback"}:
        modes.append(
            "Audio emotion model was not trained on engine-noise radio; "
            "domain mismatch may affect accuracy."
        )

    return modes
