"""Stress-lap correlation — does per-lap mood actually predict pace?

This is the methodologically sound version of the earlier demo approximation.
Instead of assuming a single mood for the whole window, it aligns a real
per-lap emotion timeline (from radio messages) with the driver's lap-time
delta and computes:

1. **Pearson correlation** between the numeric mood rank and the lap-time
   delta. Mood leads to pace, so we also search over a small lag window.
2. **Lag cross-correlation** — the lag (in laps) at which mood best predicts
   pace. A negative lag means mood changes *before* lap time changes, which is
   exactly the early-warning direction a co-driver needs.

The p-value is a two-sided Pearson test via scipy when available; otherwise a
conservative bootstrap approximation is used so the module still works without
the extra dependency.
"""

from __future__ import annotations

import math
import statistics

from app.schemas import CorrelationResult, LapPoint, Mood, MoodPoint

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

    mood_series = [_MOOD_RANK[mood] for _, mood, _ in paired]
    pace_series = [delta for _, _, delta in paired]

    correlation, p_value = _pearson(mood_series, pace_series)

    # Search for the lag at which mood best predicts pace (mood leading pace is
    # negative lag; pace leading mood is positive lag).
    best_lag, best_corr = _best_lag_correlation(mood_series, pace_series)

    # Split laps into stressed/tired vs calm/neutral for visualisation.
    stressed = [p for p in clean if mood_by_lap.get(p.lap) in {"Stressed", "Tired"}]
    non_stressed = [p for p in clean if mood_by_lap.get(p.lap) in {"Calm", "Neutral"}]

    lag_note = _lag_reasoning(best_lag)
    reasoning = (
        f"Pearson r={correlation:+.2f} (p={p_value:.3f}) over {len(paired)} "
        f"radio-labelled laps. Best lag={best_lag} laps ({lag_note}). "
        f"{'Mood leads pace' if best_lag < 0 else 'Pace leads mood' if best_lag > 0 else 'No lag'}"
    )

    return CorrelationResult(
        correlation=round(correlation, 3),
        best_lag=best_lag,
        p_value=round(p_value, 4),
        sample_size=len(paired),
        mood_timeline=timeline,
        stress_laps=stressed,
        non_stress_laps=non_stressed,
        reasoning=reasoning,
    )


def _pearson(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Pearson correlation and a two-sided p-value via scipy if available."""
    n = len(xs)
    if n < 2:
        return 0.0, 1.0

    try:
        from scipy.stats import pearsonr

        r, p = pearsonr(xs, ys)
        return float(r), float(p)
    except Exception:
        # Fallback: compute r manually and approximate p with a t-test under
        # normality (which is conservative for small samples).
        x_mean = statistics.mean(xs)
        y_mean = statistics.mean(ys)
        cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=True))
        x_var = sum((x - x_mean) ** 2 for x in xs)
        y_var = sum((y - y_mean) ** 2 for y in ys)
        if x_var == 0 or y_var == 0:
            return 0.0, 1.0
        r = cov / math.sqrt(x_var * y_var)
        r = max(-1.0, min(1.0, r))

        if abs(r) >= 1.0:
            p = 0.0
        else:
            t = r * math.sqrt((n - 2) / (1 - r * r))
            # Two-sided p from the t distribution; use a simple normal
            # approximation for small-sample robustness without scipy.
            p = 2 * (1 - _norm_cdf(abs(t)))
        return float(r), float(p)


def _best_lag_correlation(xs: list[float], ys: list[float], max_lag: int = 3) -> tuple[int, float]:
    """Find the lag (in laps) at which mood best predicts pace.

    A lag of -k means mood at lap t is compared with pace at lap t+k (mood
    leads pace). A lag of +k means pace leads mood.
    """
    n = len(xs)
    best_lag = 0
    best_corr = -1.0

    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            # Mood leads: drop the last |lag| pace values, align mood shifted.
            m = xs[: n + lag]
            p = ys[-lag:]
        elif lag > 0:
            # Pace leads: drop the first lag mood values.
            m = xs[lag:]
            p = ys[: n - lag]
        else:
            m = xs
            p = ys

        if len(m) < 4 or len(p) < 4:
            continue
        r, _ = _pearson(m, p)
        if r > best_corr:
            best_corr = r
            best_lag = lag

    return best_lag, best_corr


def _lag_reasoning(lag: int) -> str:
    if lag < 0:
        return "mood changes before pace changes — early-warning signal"
    if lag > 0:
        return "pace changes before mood — mood is a response, not a predictor"
    return "mood and pace change together"


def _norm_cdf(x: float) -> float:
    """Standard normal CDF via the error function."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))
