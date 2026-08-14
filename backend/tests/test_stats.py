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


def test_transfer_entropy_returns_bounded_value():
    rng = np.random.default_rng(1)
    cause = rng.integers(0, 4, 60)
    effect = np.roll(cause, -2)
    res = transfer_entropy(cause, effect, max_lag=3)
    assert res.statistic >= 0.0
    assert res.best_lag in (-1, -2, -3)


def test_lead_time_positive_for_clear_lead():
    rng = np.random.default_rng(2)
    cause = rng.normal(0, 1, 100)
    effect = np.zeros_like(cause)
    for t in range(3, 100):
        effect[t] = 0.6 * effect[t - 1] + 0.5 * cause[t - 3] + rng.normal(0, 0.1)
    lt = lead_time(cause, effect, max_lag=4)
    assert lt == 3
