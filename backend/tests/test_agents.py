"""Tests for the deterministic, model-free parts of PitwallEar."""

import numpy as np

from app.agents.agreement import agreement_score, cross_model_agreement
from app.agents.correlation import (
    _risk_lead_time,
    correlate_stress_to_pace,
    correlate_timeline_to_pace,
)
from app.agents.emotion import EmotionAgent
from app.agents.orchestrator import Orchestrator
from app.agents.stats import granger_causality, pearson
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


def test_agreement_score_boundary_is_agree():
    # Distance-weighted score for (Calm, Neutral) is exactly 0.75: the
    # documented threshold is >= 0.75, so this pair must count as agreement.
    assert agreement_score("Calm", "Neutral") == 0.75
    result = cross_model_agreement("Calm", "Neutral", 0.9, 0.9)
    assert result.agrees is True


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
    assert result.correlation > 0.9  # monotonic fixture: r must be near 1
    assert result.sample_size == 6


def test_correlation_none_for_constant_mood():
    laps = [
        LapPoint(lap=i, lap_time_s=86.0 + i * 0.1) for i in range(1, 7)
    ]
    timeline = [
        MoodPoint(lap=i, mood="Neutral", confidence=0.5) for i in range(1, 7)
    ]
    result = correlate_timeline_to_pace(laps, timeline)
    assert result.correlation is None
    assert "zero variance" in result.reasoning


def test_risk_lead_time_gated_on_significance():
    class FakeCausal:
        def __init__(self, lag, p):
            self.best_lag = lag
            self.p_value = p

    mood = np.array([1.0, 2.0, 3.0, 4.0])
    pace = np.array([1.0, 2.0, 3.0, 4.0])
    # Significant lead -> reported.
    lead, conf = _risk_lead_time(FakeCausal(-2, 0.01), mood, pace)
    assert lead == 2 and conf is not None and conf > 0.9
    # Same lag but insignificant -> suppressed entirely.
    lead, conf = _risk_lead_time(FakeCausal(-2, 0.42), mood, pace)
    assert lead is None and conf is None


def test_pearson_degenerate_series_returns_none():
    x = np.array([2.0, 2.0, 2.0, 2.0])
    y = np.array([1.0, 2.0, 3.0, 4.0])
    r, p = pearson(x, y)
    assert r is None and p is None


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
    # The legacy path computes no Pearson r — it must not fabricate one.
    assert correlation is not None
    assert correlation.correlation is None
    assert "single-mood approximation" in correlation.reasoning
    assert insight.action.startswith("Strong signal")


def test_action_stays_calm_when_pace_stable():
    orch = Orchestrator()
    insight, _, _ = orch.synthesise(
        TranscriptionResult(text=""),
        EmotionResult(mood="Calm", confidence=0.8, reasoning="calm"),
        PaceResult(trend="stable", delta_vs_recent_s=0.0, reasoning="stable"),
    )
    assert insight.action == "No action needed."
