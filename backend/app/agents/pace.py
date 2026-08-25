"""Pace agent — correlates mood with recent lap times from FastF1."""

from __future__ import annotations

import pandas as pd

from app.schemas import LapPoint, PaceResult


class PaceAgent:
    """Loads lap times for a driver and computes a simple pace trend.

    FastF1 is loaded lazily so the API stays responsive when no lap data is
    requested yet. When the session cannot be fetched (offline, unavailable
    season), the agent degrades to an empty trend instead of raising.
    """

    def __init__(self) -> None:
        self._cache: dict[tuple[str, str, int], list[LapPoint]] = {}

    def load_laps(self, driver: str, gp: str, year: int) -> list[LapPoint]:
        """Return clean lap times for a driver in a given Grand Prix."""
        key = (driver, gp, year)
        if key in self._cache:
            return self._cache[key]

        try:
            laps = self._fetch_laps(driver, gp, year)
        except Exception:
            # Transient failure: return empty but do NOT cache, so the next
            # request retries instead of being poisoned until restart.
            return []
        self._cache[key] = laps
        return laps

    @staticmethod
    def _fetch_laps(driver: str, gp: str, year: int) -> list[LapPoint]:
        import fastf1

        session = fastf1.get_session(year, gp, "R")
        session.load(laps=True, telemetry=False, weather=False, messages=False)
        driver_laps = session.laps.pick_drivers(driver)
        points: list[LapPoint] = []
        for _, row in driver_laps.iterrows():
            lap_time = row.get("LapTime")
            seconds = lap_time.total_seconds() if pd.notna(lap_time) else None
            # Keep laps with a plausible race lap time; skip in/out laps and
            # pit/safety-car outliers so the correlation is against genuine pace.
            if seconds is not None and 60 <= seconds <= 120:
                points.append(
                    LapPoint(
                        lap=int(row["LapNumber"]),
                        lap_time_s=seconds,
                        lap_start=str(row.get("LapStartTime") or ""),
                    )
                )
        return points

    def analyse(self, driver: str, gp: str, year: int) -> PaceResult:
        """Compute the pace trend over the last few recorded laps."""
        laps = self.load_laps(driver, gp, year)
        if not laps:
            return PaceResult(trend="unknown", laps=[], reasoning="No lap-time data available.")

        recent = [p for p in laps if p.lap_time_s is not None][-5:]
        if len(recent) < 2:
            return PaceResult(
                trend="insufficient",
                laps=laps,
                reasoning="Not enough clean laps to compute a trend.",
            )

        times = [p.lap_time_s for p in recent if p.lap_time_s is not None]
        delta = times[-1] - sum(times[:-1]) / len(times[:-1])

        if delta < -0.3:
            trend = "improving"
        elif delta > 0.3:
            trend = "slowing"
        else:
            trend = "stable"

        reasoning = (
            f"Last lap {times[-1]:.2f}s is {delta:+.2f}s vs the previous "
            f"{len(times) - 1} laps."
        )
        return PaceResult(
            trend=trend,
            delta_vs_recent_s=round(delta, 3),
            laps=laps,
            reasoning=reasoning,
        )
