"""Cross-model agreement — does the audio tone agree with the transcript?"""

from __future__ import annotations

from app.schemas import AgreementResult, Mood

# When both models are real (not fallback), a disagreement between these mood
# pairs is a strong signal worth flagging. Same-mood and nearby-mood pairs are
# treated as agreement.
_MOOD_DISTANCE: dict[tuple[Mood, Mood], float] = {
    ("Calm", "Calm"): 0.0,
    ("Calm", "Neutral"): 0.25,
    ("Neutral", "Calm"): 0.25,
    ("Stressed", "Stressed"): 0.0,
    ("Stressed", "Tired"): 0.35,
    ("Tired", "Stressed"): 0.35,
    ("Tired", "Tired"): 0.0,
    ("Neutral", "Neutral"): 0.0,
    ("Calm", "Stressed"): 1.0,
    ("Stressed", "Calm"): 1.0,
    ("Calm", "Tired"): 0.8,
    ("Tired", "Calm"): 0.8,
    ("Neutral", "Stressed"): 0.6,
    ("Stressed", "Neutral"): 0.6,
    ("Neutral", "Tired"): 0.5,
    ("Tired", "Neutral"): 0.5,
}


def agreement_score(audio_mood: Mood, text_mood: Mood) -> float:
    """Return a 0..1 agreement score for two moods (1 = full agreement)."""
    if audio_mood == text_mood:
        return 1.0
    return 1.0 - _MOOD_DISTANCE.get((audio_mood, text_mood), 0.5)


def cross_model_agreement(
    audio_mood: Mood,
    text_mood: Mood,
    audio_confidence: float,
    text_confidence: float,
) -> AgreementResult:
    """Compare audio-tone mood with transcript mood.

    The two models see different things: audio reads *how* the driver says it,
    text reads *what* they say. When they disagree (for example, a calm voice
    describing a serious car problem), that mismatch is itself a signal — it can
    mean the driver is masking stress, or that the problem is real but the
    driver is staying composed. This is the novel part the demo showcases.
    """
    score = round(agreement_score(audio_mood, text_mood), 3)
    agrees = score >= 0.75

    # A low confidence on either side weakens the agreement claim.
    confidence_floor = min(audio_confidence, text_confidence)
    if confidence_floor < 0.4:
        reasoning = (
            "Low confidence on one or both models, so agreement is provisional. "
            f"Audio={audio_mood} ({audio_confidence:.0%}), text={text_mood} ({text_confidence:.0%})."
        )
    elif agrees:
        reasoning = (
            f"Audio tone ({audio_mood}) and transcript emotion ({text_mood}) agree "
            f"(score {score:.2f}). The signal is internally consistent."
        )
    else:
        reasoning = (
            f"Audio tone says {audio_mood} but the transcript reads {text_mood} "
            f"(score {score:.2f}). The driver's words and tone diverge — check "
            f"whether they are masking a problem or underplaying it."
        )

    return AgreementResult(
        agrees=agrees,
        agreement_score=score,
        audio_mood=audio_mood,
        text_mood=text_mood,
        reasoning=reasoning,
    )
