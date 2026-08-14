"""Stress-lap correlation — does per-lap mood actually predict pace?

This module aligns a real per-lap emotion timeline (from radio messages) with
the driver's lap-time deltas and computes:

1. **Pearson correlation** between the numeric mood rank and the lap-time delta.
2. **Causal lead-lag inference** via Granger causality (and transfer entropy
   fallback) to test whether mood *leads* pace rather than merely co-moving.
3. **Risk lead-time** — the number of laps mood changes before pace, which is
   the early-warning property a co-driver needs.
"""

from __future__ import annotations

import math
import statistics

import numpy as np

from app.agents import stats
from app.schemas import (
    CausalResult,
    CorrelationResult,
    LapPoint,
    Mood,
    MoodPoint,
)

_MOOD_RANK: dict[Mood, float] = {"Calm": 1.0, "Neutral": 2.0, "Tired": 3.0, "Stressed": 4.0}


def correlate_stress_to_pace(
    laps: list[LapPoint],
    mood: Mood,
) -> CorrelationResult:
    """Legacy single-mood approximation.

    This is NOT the production method; it exists only so callers without a
    per-lap timeline still get a value. It propagates one mood across the lap
    window and compares the first half against the second half.
    """
    clean = [p for p in laps if p.lap_time_s is not None]
    if len(clean) < 4:
        return CorrelationResult(
            correlation=None,
            sample_size=len(clean),
            reasoning="Not enough clean laps to estimate a stress-pace link.",
        )

    half = len(clean) // 2
    baseline = clean[:half]
    recent = clean[half:]
    baseline_mean = statistics.mean(p.lap_time_s for p in baseline)
    recent_mean = statistics.mean(p.lap_time_s for p in recent)
    delta = recent_mean - baseline_mean

    stressed_moods = {"Stressed", "Tired"}
    if mood in stressed_moods:
        correlation = max(-1.0, min(1.0, delta / 0.5))
        sign = "slower" if delta > 0.2 else ("faster" if delta < -0.2 else "stable")
        reasoning = (
            f"Negative mood ({mood}) and recent pace is {sign} "
            f"({delta:+.2f}s vs baseline). "
            f"Correlation {correlation:+.2f} on {len(clean)} laps. "
            f"(single-mood approximation, not a real per-lap timeline)"
        )
    else:
        correlation = max(-1.0, min(1.0, -delta / 0.5))
        sign = "slower" if delta > 0.2 else ("faster" if delta < -0.2 else "stable")
        reasoning = (
            f"Non-negative mood ({mood}) and recent pace is {sign} "
            f"({delta:+.2f}s vs baseline). "
            f"Correlation {correlation:+.2f} on {len(clean)} laps. "
            f"(single-mood approximation, not a real per-lap timeline)"
        )

    return CorrelationResult(
        correlation=round(correlation, 3),
        best_lag=0,
        p_value=None,
        sample_size=len(clean),
        stress_laps=recent,
        non_stress_laps=baseline,
        reasoning=reasoning,
    )


def correlate_timeline_to_pace(
    laps: list[LapPoint],
    timeline: list[MoodPoint],
) -> CorrelationResult:
    """Correlate a per-lap mood timeline with lap-time deltas.

    ``laps`` is the driver's clean lap list; ``timeline`` is the per-lap mood
    from radio messages. Laps without a radio label are omitted from the
    correlation, so the sample size is reported honestly.
    """
    clean = [p for p in laps if p.lap_time_s is not None]
    if not clean:
        return CorrelationResult(
            correlation=None,
            sample_size=0,
            mood_timeline=timeline,
            reasoning="No clean lap-time data available.",
        )

    # Map lap -> mood.
    mood_by_lap = {m.lap: m.mood for m in timeline}
    if not mood_by_lap:
        return CorrelationResult(
            correlation=None,
            sample_size=len(clean),
            mood_timeline=timeline,
            stress_laps=[],
            non_stress_laps=clean,
            reasoning="No per-lap radio mood labels available.",
        )

    # Compute each lap's delta from the driver's own session mean. This removes
    # the circuit/compound baseline so we are comparing mood against *relative*
    # pace, not absolute lap time.
    mean_time = statistics.mean(p.lap_time_s for p in clean)
    deltas = {p.lap: p.lap_time_s - mean_time for p in clean}

    paired = [(lap, mood_by_lap[lap], deltas[lap]) for lap in mood_by_lap if lap in deltas]
    paired.sort(key=lambda x: x[0])

    if len(paired) < 4:
        return CorrelationResult(
            correlation=None,
            sample_size=len(paired),
            mood_timeline=timeline,
            stress_laps=[],
            non_stress_laps=clean,
            reasoning=f"Only {len(paired)} laps have both radio and pace data; need at least 4.",
        )

    mood_series = np.array([_MOOD_RANK[mood] for _, mood, _ in paired], dtype=float)
    pace_series = np.array([delta for _, _, delta in paired], dtype=float)

    correlation, p_value = stats.pearson(mood_series, pace_series)

    # Split laps into stressed/tired vs calm/neutral for visualisation.
    stressed = [p for p in clean if mood_by_lap.get(p.lap) in {"Stressed", "Tired"}]
    non_stressed = [p for p in clean if mood_by_lap.get(p.lap) in {"Calm", "Neutral"}]

    causal_raw = _causal_lead(mood_series, pace_series)
    causal = CausalResult(
        method=causal_raw.method,
        statistic=causal_raw.statistic,
        p_value=causal_raw.p_value,
        best_lag=causal_raw.best_lag,
        direction=causal_raw.direction,
        sample_size=causal_raw.sample_size,
        reasoning=causal_raw.reasoning,
    )
    lead_laps, lead_conf = _risk_lead_time(causal, mood_series, pace_series)

    reasoning = (
        f"Pearson r={correlation:+.2f} (p={p_value:.3f}) over {len(paired)} "
        f"radio-labelled laps. {causal.reasoning}"
    )

    return CorrelationResult(
        correlation=round(correlation, 3),
        best_lag=causal.best_lag,
        p_value=round(p_value, 4),
        sample_size=len(paired),
        mood_timeline=timeline,
        stress_laps=stressed,
        non_stress_laps=non_stressed,
        reasoning=reasoning,
        causal=causal,
        risk_lead_time_laps=lead_laps,
        lead_time_confidence=lead_conf,
    )


def _causal_lead(mood: np.ndarray, pace: np.ndarray):
    """Run causal lead-lag analysis, choosing the appropriate method."""
    # Granger needs at least ~6 points per lag; otherwise fall back to TE.
    if mood.size >= 8:
        return stats.granger_causality(mood, pace)
    return stats.transfer_entropy(mood, pace)


def _risk_lead_time(
    causal,
    mood: np.ndarray,
    pace: np.ndarray,
) -> tuple[int | None, float | None]:
    """Convert a causal result into a lead-time headline with a confidence.

    Lead time is only reported when mood is found to *lead* pace. The confidence
    is 1 - p from the causal test, floored at 0.5 so a weak result is not
    presented as certainty.
    """
    if causal.best_lag >= 0:
        return None, None
    lead = abs(causal.best_lag)
    conf = round(max(0.5, 1.0 - causal.p_value), 3)
    return lead, conf
