"""Multi-race aggregation runner.

Builds a persistent store of paired mood-vs-pace samples across many drivers and
Grands Prix, then runs the causal lead-lag analysis on the pooled sample. This
turns the single-race `n < 10` limitation into a statistically meaningful result.

Uses SQLite (stdlib) so the pipeline runs with zero extra dependencies.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from app.agents import stats
from app.agents.correlation import _MOOD_RANK


@dataclass
class AggregationRow:
    driver: str
    gp: str
    year: int
    lap: int
    mood: str
    mood_rank: float
    pace_delta: float


def _db_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "aggregation.db"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS samples (
            driver TEXT NOT NULL,
            gp TEXT NOT NULL,
            year INTEGER NOT NULL,
            lap INTEGER NOT NULL,
            mood TEXT NOT NULL,
            mood_rank REAL NOT NULL,
            pace_delta REAL NOT NULL,
            PRIMARY KEY (driver, gp, year, lap)
        )
        """
    )
    return conn


def add_samples(rows: list[AggregationRow]) -> int:
    """Persist paired samples, replacing any existing row for the same lap."""
    if not rows:
        return 0
    conn = _connect()
    try:
        conn.executemany(
            """
            INSERT OR REPLACE INTO samples
            (driver, gp, year, lap, mood, mood_rank, pace_delta)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (r.driver, r.gp, r.year, r.lap, r.mood, r.mood_rank, r.pace_delta)
                for r in rows
            ],
        )
        conn.commit()
        return len(rows)
    finally:
        conn.close()


def all_samples() -> list[AggregationRow]:
    """Return every persisted sample sorted by driver, gp, lap."""
    conn = _connect()
    try:
        cur = conn.execute(
            """
            SELECT driver, gp, year, lap, mood, mood_rank, pace_delta
            FROM samples
            ORDER BY driver, gp, year, lap
            """
        )
        return [AggregationRow(*row) for row in cur.fetchall()]
    finally:
        conn.close()


def clear_samples() -> None:
    conn = _connect()
    try:
        conn.execute("DELETE FROM samples")
        conn.commit()
    finally:
        conn.close()


def pooled_causal_analysis(rows: list[AggregationRow]) -> dict:
    """Run causal lead-lag analysis on the pooled mood/pace series.

    Because each race is a separate time series, the pooled analysis concatenates
    within-driver, within-race sequences with NaNs as boundaries. A simpler and
    more defensible approach here is to aggregate the *direction and magnitude*
    of lead-lag per race and then test across races. This function implements the
    latter: it reports the distribution of best lags and the fraction of races
    where mood leads pace.
    """
    if not rows:
        return {
            "sample_size": 0,
            "races": 0,
            "mood_leads_races": 0,
            "mood_leads_fraction": None,
            "median_lead_laps": None,
            "reasoning": "No pooled samples available.",
        }

    by_race: dict[tuple[str, str, int], list[AggregationRow]] = {}
    for r in rows:
        by_race.setdefault((r.driver, r.gp, r.year), []).append(r)

    lead_laps: list[int] = []
    n_leads = 0
    n_races_with_result = 0

    for key, race_rows in by_race.items():
        race_rows.sort(key=lambda x: x.lap)
        mood = np.array([r.mood_rank for r in race_rows], dtype=float)
        pace = np.array([r.pace_delta for r in race_rows], dtype=float)
        if mood.size < 8:
            continue
        causal = stats.granger_causality(mood, pace)
        n_races_with_result += 1
        if causal.best_lag < 0:
            n_leads += 1
            lead_laps.append(abs(causal.best_lag))

    if n_races_with_result == 0:
        return {
            "sample_size": len(rows),
            "races": len(by_race),
            "mood_leads_races": 0,
            "mood_leads_fraction": None,
            "median_lead_laps": None,
            "reasoning": "No race had enough paired samples for causal analysis.",
        }

    fraction = n_leads / n_races_with_result
    median_lead = float(np.median(lead_laps)) if lead_laps else None

    return {
        "sample_size": len(rows),
        "races": len(by_race),
        "mood_leads_races": n_leads,
        "mood_leads_fraction": round(fraction, 3),
        "median_lead_laps": round(median_lead, 1) if median_lead is not None else None,
        "reasoning": (
            f"Mood leads pace in {n_leads}/{n_races_with_result} races "
            f"({fraction:.0%}), median lead {median_lead:.1f} laps "
            f"across {len(rows)} paired samples."
        ),
    }


def build_rows_from_analysis(
    driver: str,
    gp: str,
    year: int,
    laps: list,
    timeline: list,
) -> list[AggregationRow]:
    """Convert an analysis result into rows for the aggregation store."""
    clean = [p for p in laps if p.lap_time_s is not None]
    if not clean:
        return []
    mean_time = sum(p.lap_time_s for p in clean) / len(clean)
    mood_by_lap = {m.lap: m.mood for m in timeline}

    rows: list[AggregationRow] = []
    for p in clean:
        if p.lap in mood_by_lap:
            rows.append(
                AggregationRow(
                    driver=driver,
                    gp=gp,
                    year=year,
                    lap=p.lap,
                    mood=mood_by_lap[p.lap],
                    mood_rank=_MOOD_RANK[mood_by_lap[p.lap]],
                    pace_delta=round(p.lap_time_s - mean_time, 4),
                )
            )
    return rows
