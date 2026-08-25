"""Hermetic tests for the causal statistics primitives."""
import numpy as np

from app.agents.stats import (
    granger_causality,
    lead_time,
    mood_rank,
    pearson,
    transfer_entropy,
)


def test_mood_rank_order():
    assert mood_rank("Calm") < mood_rank("Neutral")
    assert mood_rank("Neutral") < mood_rank("Tired")
    assert mood_rank("Tired") < mood_rank("Stressed")


def test_pearson_perfect_positive():
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    r, p = pearson(x, x)
    assert r == 1.0
    assert p < 0.05


def test_granger_detects_clear_lead():
    rng = np.random.default_rng(0)
    # cause leads effect by 2 steps
    cause = rng.normal(0, 1, 80)
    effect = np.zeros_like(cause)
    for t in range(2, 80):
        effect[t] = 0.7 * effect[t - 1] + 0.4 * cause[t - 2] + rng.normal(0, 0.1)
    res = granger_causality(cause, effect, max_lag=4)
    assert res.best_lag == -2
    assert res.p_value < 0.05
    assert res.direction == "mood leads pace"


def test_transfer_entropy_detects_reverse_direction():
    rng = np.random.default_rng(1)
    cause = rng.integers(0, 4, 60)
    # effect[t] = cause[t+2]: effect *leads* cause, so the bidirectional test
    # must report a positive lag ("pace leads mood"), not a fabricated mood-lead.
    effect = np.roll(cause, -2)
    res = transfer_entropy(cause, effect, max_lag=3)
    assert res.statistic >= 0.0
    assert res.best_lag == 2
    assert res.direction == "pace leads mood"


def test_granger_independent_series_not_significant():
    rng = np.random.default_rng(7)
    a = rng.normal(0, 1, 60)
    b = rng.normal(0, 1, 60)
    res = granger_causality(a, b, max_lag=3)
    # Bidirectional selection always reports the smaller-p direction; for
    # independent series it must be clearly insignificant.
    assert res.p_value >= 0.05


def test_granger_skips_meaningless_dof():
    # n=8 with max_lag=3 gives dof < 5 for every lag: nothing may be reported.
    rng = np.random.default_rng(9)
    a = rng.normal(0, 1, 8)
    b = rng.normal(0, 1, 8)
    res = granger_causality(a, b, max_lag=3)
    assert res.best_lag == 0
    assert res.direction == "no directional lead"


def test_lead_time_positive_for_clear_lead():
    rng = np.random.default_rng(2)
    cause = rng.normal(0, 1, 100)
    effect = np.zeros_like(cause)
    for t in range(3, 100):
        effect[t] = 0.6 * effect[t - 1] + 0.5 * cause[t - 3] + rng.normal(0, 0.1)
    lt = lead_time(cause, effect, max_lag=4)
    assert lt == 3
