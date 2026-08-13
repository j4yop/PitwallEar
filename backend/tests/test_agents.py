"""Tests for the deterministic, model-free parts of PitwallEar."""

from app.agents.agreement import agreement_score, cross_model_agreement
from app.agents.correlation import correlate_timeline_to_pace
from app.agents.emotion import EmotionAgent
from app.agents.orchestrator import Orchestrator
from app.schemas import (
    EmotionResult,
    LapPoint,
    MoodPoint,
    PaceResult,
    TranscriptionResult,
)


def test_audio_mood_mapping():
    assert EmotionAgent._audio_to_mood("angry") == "Stressed"
    assert EmotionAgent._audio_to_mood("calm") == "Calm"
    assert EmotionAgent._audio_to_mood("sad") == "Tired"
    assert EmotionAgent._audio_to_mood("neutral") == "Neutral"


def test_text_mood_mapping():
    assert EmotionAgent._text_to_mood("anger") == "Stressed"
    assert EmotionAgent._text_to_mood("sadness") == "Tired"
    assert EmotionAgent._text_to_mood("joy") == "Calm"


def test_agreement_score_same_and_opposite():
    assert agreement_score("Calm", "Calm") == 1.0
    assert agreement_score("Stressed", "Calm") == 0.0


def test_cross_model_agreement_detects_conflict():
    result = cross_model_agreement("Calm", "Stressed", 0.9, 0.85)
    assert result.agrees is False
    assert "diverge" in result.reasoning.lower()


def test_timeline_correlation_computes_bounded_value():
    laps = [
        LapPoint(lap=1, lap_time_s=86.0),
        LapPoint(lap=2, lap_time_s=86.1),
        LapPoint(lap=3, lap_time_s=86.3),
        LapPoint(lap=4, lap_time_s=87.0),
        LapPoint(lap=5, lap_time_s=87.5),
        LapPoint(lap=6, lap_time_s=87.8),
    ]
    timeline = [
        MoodPoint(lap=1, mood="Calm", confidence=0.9),
        MoodPoint(lap=2, mood="Calm", confidence=0.9),
        MoodPoint(lap=3, mood="Neutral", confidence=0.8),
        MoodPoint(lap=4, mood="Stressed", confidence=0.7),
        MoodPoint(lap=5, mood="Stressed", confidence=0.8),
        MoodPoint(lap=6, mood="Stressed", confidence=0.9),
    ]
    result = correlate_timeline_to_pace(laps, timeline)
    assert result.correlation is not None
    assert -1.0 <= result.correlation <= 1.0
    assert result.sample_size == 6


def test_fallback_synthesis_links_mood_and_pace():
    orch = Orchestrator()
    laps = [
        LapPoint(lap=1, lap_time_s=86.0),
        LapPoint(lap=2, lap_time_s=86.1),
        LapPoint(lap=3, lap_time_s=86.4),
        LapPoint(lap=4, lap_time_s=87.0),
        LapPoint(lap=5, lap_time_s=87.6),
    ]
    insight, agreement, correlation = orch.synthesise(
        TranscriptionResult(text="This car is undriveable."),
        EmotionResult(mood="Stressed", confidence=0.9, reasoning="dominant angry"),
        PaceResult(trend="slowing", delta_vs_recent_s=0.5, laps=laps, reasoning="slower"),
    )
    assert "stressed" in insight.summary.lower()
    assert "slower" in insight.summary.lower()
    assert correlation is not None
    assert correlation.correlation is not None and correlation.correlation > 0.0
    assert insight.action.startswith("Strong signal")


def test_action_stays_calm_when_pace_stable():
    orch = Orchestrator()
    insight, _, _ = orch.synthesise(
        TranscriptionResult(text=""),
        EmotionResult(mood="Calm", confidence=0.8, reasoning="calm"),
        PaceResult(trend="stable", delta_vs_recent_s=0.0, reasoning="stable"),
    )
    assert insight.action == "No action needed."
