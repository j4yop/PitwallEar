"""Tests for the pooled multi-race significance layer (aggregation.py)."""

import numpy as np
import pytest

from app.agents import aggregation
from app.agents.aggregation import (
    AggregationRow,
    add_samples,
    all_samples,
    build_rows_from_analysis,
    clear_samples,
    pooled_causal_analysis,
)
from app.schemas import LapPoint, MoodPoint


@pytest.fixture(autouse=True)
def _tmp_db(monkeypatch, tmp_path):
    monkeypatch.setattr(aggregation, "_db_path", lambda: tmp_path / "agg.db")


def _row(driver="VER", gp="Spa", year=2024, lap=1, mood_rank=3.0, pace_delta=0.2):
    return AggregationRow(
        driver=driver, gp=gp, year=year, lap=lap,
        mood="Stressed" if mood_rank >= 3 else "Calm",
        mood_rank=mood_rank, pace_delta=pace_delta,
    )


def test_empty_store_shape():
    out = pooled_causal_analysis(all_samples())
    assert out["sample_size"] == 0
    assert out["mood_leads_fraction"] is None
    assert "No pooled samples" in out["reasoning"]


def test_pk_replace_keeps_one_row_per_lap():
    add_samples([_row(lap=1, pace_delta=0.1)])
    add_samples([_row(lap=1, pace_delta=0.9)])  # same (driver,gp,year,lap)
    rows = all_samples()
    assert len(rows) == 1
    assert rows[0].pace_delta == pytest.approx(0.9)


def test_pooled_result_reports_median_lead():
    # Two races where mood rises two laps before pace does (with noise so the
    # OLS residuals are never exactly zero).
    rng = np.random.default_rng(42)
    rows = []
    for gp in ("Spa", "Monza"):
        for lap in range(1, 13):
            mood = 4.0 if lap >= 5 else 1.0
            delta = (1.0 if lap >= 7 else 0.0) + rng.normal(0, 0.05)
            rows.append(_row(gp=gp, lap=lap, mood_rank=mood, pace_delta=round(delta, 4)))
    add_samples(rows)
    out = pooled_causal_analysis(all_samples())
    assert out["races"] == 2
    assert out["sample_size"] == 24
    assert out["mood_leads_races"] >= 1
    assert out["median_lead_laps"] is not None


def test_no_leads_reports_na_without_crashing():
    # Regression: constant mood -> no race leads; median formatting must not 500.
    rows = [
        _row(gp=g, lap=l, mood_rank=1.0, pace_delta=0.1 * l)
        for g in ("Spa", "Monza")
        for l in range(1, 11)
    ]
    add_samples(rows)
    out = pooled_causal_analysis(all_samples())
    assert out["median_lead_laps"] is None
    assert "n/a" in out["reasoning"] or out["mood_leads_fraction"] == 0.0


def test_build_rows_from_analysis_pairs_labels_and_laps():
    laps = [LapPoint(lap=i, lap_time_s=86.0 + i * 0.2) for i in range(1, 7)]
    timeline = [
        MoodPoint(lap=1, mood="Stressed", confidence=0.8),
        MoodPoint(lap=99, mood="Tired", confidence=0.8),  # lap without pace data
    ]
    rows = build_rows_from_analysis("VER", "Monaco", 2024, laps, timeline)
    assert len(rows) == 1
    assert rows[0].lap == 1 and rows[0].gp == "Monaco"


def test_add_samples_rejects_unknown_driver():
    from app.agents.aggregation import _row_is_valid

    assert not _row_is_valid(_row(driver="XX9"))
    assert _row_is_valid(_row(driver="VER"))


def test_add_samples_rejects_garbage_year_and_lap():
    from app.agents.aggregation import _row_is_valid

    bad = AggregationRow("VER", "Spa", 1999, 1, "Calm", 1.0, 0.1)
    bad_lap = AggregationRow("VER", "Spa", 2024, -3, "Calm", 1.0, 0.1)
    bad_mood = AggregationRow("VER", "Spa", 2024, 1, "Angry", 9.9, 0.1)
    assert not _row_is_valid(bad)
    assert not _row_is_valid(bad_lap)
    assert not _row_is_valid(bad_mood)


def test_add_samples_filters_before_persist(tmp_path, monkeypatch):
    monkeypatch.setattr(aggregation, "_db_path", lambda: tmp_path / "f.db")
    good = _row(lap=1)
    bad = AggregationRow("HACK", "Evil GP; DROP", 2024, 2, "Stressed", 4.0, 0.5)
    added = add_samples([good, bad])
    assert added == 1
    rows = all_samples()
    assert len(rows) == 1 and rows[0].driver == "VER"
