"""Statistical primitives for PitwallEar's causal lead-lag analysis.

Everything here is dependency-light (numpy + scipy only) and deterministic so it
can be unit-tested hermetically. The two headline methods are:

* **Granger causality** — does the past of one series improve prediction of
  another beyond its own history?
* **Transfer entropy** — does knowing the past state of one series reduce the
  uncertainty in another, without assuming linearity?
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

import numpy as np

from app.schemas import LapPoint, Mood, MoodPoint

_MOOD_RANK: dict[Mood, float] = {"Calm": 1.0, "Neutral": 2.0, "Tired": 3.0, "Stressed": 4.0}


@dataclass
class CausalResult:
    """Output of a mood -> pace lead-lag test."""

    method: str
    statistic: float
    p_value: float
    best_lag: int
    direction: str
    sample_size: int
    reasoning: str


def mood_rank(mood: Mood) -> float:
    return _MOOD_RANK[mood]


def pearson(xs: np.ndarray, ys: np.ndarray) -> tuple[float, float]:
    """Pearson correlation with a two-sided p-value via scipy."""
    from scipy.stats import pearsonr  # type: ignore

    if xs.size < 3 or ys.size < 3:
        return 0.0, 1.0
    r, p = pearsonr(xs, ys)
    return float(r), float(p)


def _lag_series(a: np.ndarray, lag: int) -> np.ndarray:
    """Shift ``a`` so the pair (a[t], a[t+lag]) can be compared.

    A negative lag means ``a`` leads the other series: the first ``|lag|`` values
    of ``a`` are dropped and the last ``|lag|`` values of the other are dropped.
    """
    if lag == 0:
        return a
    if lag < 0:
        return a[:lag]
    return a[lag:]


def _ols_rss(y: np.ndarray, X: np.ndarray) -> float:
    """Residual sum of squares for an OLS fit with intercept."""
    n = y.size
    design = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    return float(resid @ resid)


def granger_causality(
    cause: np.ndarray,
    effect: np.ndarray,
    max_lag: int = 3,
) -> CausalResult:
    """Test whether ``cause`` Granger-causes ``effect``.

    Fits two vector autoregressions at every lag in ``[1, max_lag]`` and returns
    the lag with the strongest evidence (smallest p-value). A negative sign in
    the returned ``best_lag`` means cause leads effect (mood leads pace).
    """
    from scipy.stats import f as f_dist  # type: ignore

    n = min(cause.size, effect.size)
    best_lag = 0
    best_stat = float("inf")
    best_p = 1.0

    for lag in range(1, max_lag + 1):
        # Pair cause[t] with effect[t + lag]: cause leads effect.
        c = cause[: n - lag]
        e = effect[lag:n]
        if c.size < 6:
            continue

        # Restricted: effect on its own history.
        hist = np.column_stack([effect[lag - i - 1 : n - i - 1] for i in range(lag)])
        rss_r = _ols_rss(e, hist)

        # Unrestricted: add cause history.
        full = np.column_stack([hist, np.column_stack([cause[lag - i - 1 : n - i - 1] for i in range(lag)])])
        rss_u = _ols_rss(e, full)

        k = lag  # number of added regressors
        dof = n - lag - (2 * lag + 1)
        if dof <= 0 or rss_u <= 0:
            continue

        f_stat = ((rss_r - rss_u) / k) / (rss_u / dof)
        if f_stat < 0:
            f_stat = 0.0
        p = float(f_dist.sf(f_stat, k, dof))

        if p < best_p:
            best_p = p
            best_stat = float(f_stat)
            best_lag = -lag

    direction = (
        "mood leads pace"
        if best_lag < 0
        else "pace leads mood"
        if best_lag > 0
        else "no directional lead"
    )
    return CausalResult(
        method="granger",
        statistic=round(best_stat, 4),
        p_value=round(best_p, 6),
        best_lag=best_lag,
        direction=direction,
        sample_size=n,
        reasoning=_causal_reasoning("Granger causality", best_lag, best_p),
    )


def transfer_entropy(
    cause: np.ndarray,
    effect: np.ndarray,
    max_lag: int = 3,
    bins: int = 4,
) -> CausalResult:
    """Estimate transfer entropy from ``cause`` to ``effect`` with a simple
    histogram estimator. Returns the lag with the largest information transfer.
    """
    from scipy.stats import chi2  # type: ignore

    n = min(cause.size, effect.size)
    best_lag = 0
    best_te = -1.0
    best_p = 1.0

    for lag in range(1, max_lag + 1):
        c = cause[: n - lag]
        e = effect[lag:n]
        e_past = effect[: n - lag]
        if c.size < 8:
            continue

        # Discretise with quantile bins so the estimator is scale-free.
        c_q = _quantile_bin(c, bins)
        e_q = _quantile_bin(e, bins)
        ep_q = _quantile_bin(e_past, bins)

        te = _te_hist(ep_q, c_q, e_q)
        if te > best_te:
            best_te = te
            best_lag = -lag

    # A rough significance value: 2*TE follows chi2((bins-1)^2 * bins) under a
    # Gaussian surrogate in many histogram TE estimators. This is an
    # approximation and is labelled as such in the reasoning.
    dof = max(1, ((bins - 1) ** 2) * bins)
    p = float(chi2.sf(2 * best_te * n, dof)) if best_te > 0 else 1.0

    direction = (
        "mood leads pace"
        if best_lag < 0
        else "pace leads mood"
        if best_lag > 0
        else "no directional lead"
    )
    return CausalResult(
        method="transfer_entropy",
        statistic=round(best_te, 4),
        p_value=round(p, 6),
        best_lag=best_lag,
        direction=direction,
        sample_size=n,
        reasoning=_causal_reasoning("transfer entropy", best_lag, p),
    )


def _quantile_bin(x: np.ndarray, bins: int) -> np.ndarray:
    """Map values to quantile bins 0..bins-1."""
    if np.unique(x).size < bins:
        return np.zeros_like(x, dtype=int)
    return np.digitize(x, np.quantile(x, np.linspace(0, 1, bins + 1)[1:-1])).astype(int)


def _entropy(vals: np.ndarray) -> float:
    """Shannon entropy of a discrete array."""
    counts = np.bincount(vals)
    probs = counts[counts > 0] / vals.size
    return float(-np.sum(probs * np.log(probs)))


def _joint_entropy(a: np.ndarray, b: np.ndarray) -> float:
    """Joint entropy of two discrete arrays over the same bin count."""
    bins = int(max(a.max(), b.max())) + 1
    joint = np.zeros((bins, bins))
    for av, bv in zip(a, b, strict=True):
        joint[av, bv] += 1
    probs = joint[joint > 0] / a.size
    return float(-np.sum(probs * np.log(probs)))


def _joint_entropy3(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Joint entropy of three discrete arrays over the same bin count."""
    bins = int(max(a.max(), b.max(), c.max())) + 1
    joint = np.zeros((bins, bins, bins))
    for av, bv, cv in zip(a, b, c, strict=True):
        joint[av, bv, cv] += 1
    probs = joint[joint > 0] / a.size
    return float(-np.sum(probs * np.log(probs)))


def _te_hist(source: np.ndarray, cause: np.ndarray, target: np.ndarray) -> float:
    """Histogram estimator of TE(cause -> target | source).

    TE = H(target, source) + H(source, cause) - H(target, source, cause) - H(source)
    """
    h_ts = _joint_entropy(target, source)
    h_sc = _joint_entropy(source, cause)
    h_tsc = _joint_entropy3(target, source, cause)
    h_s = _entropy(source)
    return max(0.0, h_ts + h_sc - h_tsc - h_s)


def _causal_reasoning(method: str, lag: int, p: float) -> str:
    if lag < 0:
        lead = f"mood changes before pace by {abs(lag)} lap(s) — early-warning signal"
    elif lag > 0:
        lead = f"pace changes before mood by {lag} lap(s) — mood is a response"
    else:
        lead = "no directional lead found"
    return f"{method}: best lead-lag {lag}, p={p:.4f} ({lead})."


def lead_time(cause: np.ndarray, effect: np.ndarray, max_lag: int = 3) -> int:
    """Return the number of steps ``cause`` leads ``effect`` (positive integer).

    Uses Granger causality as the primary test and falls back to transfer
    entropy when the sample is too small for a stable linear fit.
    """
    n = min(cause.size, effect.size)
    if n >= 8:
        res = granger_causality(cause, effect, max_lag=max_lag)
    else:
        res = transfer_entropy(cause, effect, max_lag=max_lag)
    return abs(res.best_lag) if res.best_lag < 0 else 0
