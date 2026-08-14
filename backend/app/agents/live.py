"""Live/near-real-time session mode.

PitwallEar's post-hoc pipeline becomes a live co-driver by pointing at the most
recent race session and replaying the analysis on the freshest lap window.

Live pace is sourced from FastF1, which reads F1's official live timing data
during a race weekend (its cache refreshes on each call while the session is
active). Live radio *audio* is not freely available — OpenF1 gates its live
audio tier behind a sponsor plan — so the radio timeline stays honestly labelled
as near-real-time replay unless sponsor access is configured.
"""

from __future__ import annotations

import time

from app.agents.pace import PaceAgent
from app.agents.radio_timeline import RadioTimelineAgent


def live_pace(driver: str, gp: str, year: int) -> dict:
    """Return the freshest lap-time data available for a driver.

    FastF1 pulls from F1's official timing source and updates live during a
    session. Outside a session it serves the latest completed data. The
    ``is_live`` flag is a best-effort freshness check based on the most recent
    lap timestamp.
    """
    pace = PaceAgent()
    pace_result = pace.analyse(driver, gp, year)
    laps = pace_result.laps

    is_live = False
    latest_lap_ts = ""
    if laps:
        latest = laps[-1]
        latest_lap_ts = latest.lap_start or ""
        if latest_lap_ts:
            try:
                from datetime import datetime, timezone

                dt = datetime.fromisoformat(latest_lap_ts)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                age_s = (datetime.now(timezone.utc) - dt).total_seconds()
                # A lap timestamp within ~5 minutes suggests an active session.
                is_live = age_s < 300
            except Exception:
                is_live = False

    return {
        "driver": driver,
        "gp": gp,
        "year": year,
        "is_live": is_live,
        "trend": pace_result.trend,
        "delta_vs_recent_s": pace_result.delta_vs_recent_s,
        "latest_laps": [p.model_dump() for p in laps[-5:]],
        "reasoning": pace_result.reasoning,
        "source": "FastF1 official live timing",
    }


def live_snapshot(driver: str, gp: str, year: int) -> dict:
    """Return a live-ready snapshot of pace and mood for the latest laps.

    Pace is live (FastF1); radio is near-real-time replay of the most recent
    complete session. Both labels are explicit so the product never overclaims.
    """
    pace_data = live_pace(driver, gp, year)
    timeline = RadioTimelineAgent().build_timeline(driver, gp, year)

    return {
        "driver": driver,
        "gp": gp,
        "year": year,
        "mode": "live" if pace_data["is_live"] else "near-real-time-replay",
        "pace": pace_data,
        "mood_timeline": [p.model_dump() for p in timeline],
        "caveat": (
            "Pace is live from FastF1 (official timing). Radio audio is a "
            "near-real-time replay: OpenF1's live audio tier is sponsor-gated."
        ),
    }
