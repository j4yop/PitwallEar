"""Batch runner for the PitwallEar significance layer.

Reuses the production agents (transcription, emotion, radio timeline, pace) to
process several real races and persist paired mood-vs-pace samples. This is the
script that produces the *actual* pooled result rather than a theoretical one.

Usage:
    python -m app.batch_runner [--races 4]
"""

from __future__ import annotations

import argparse
import time

from app.agents.aggregation import add_samples, build_rows_from_analysis, pooled_causal_analysis
from app.agents.pace import PaceAgent
from app.agents.radio_timeline import RadioTimelineAgent

# 2024 races known to have complete free OpenF1 radio data.
# FastF1 GP names must match its event resolver (use full official names).
RACES = [
    ("Belgian Grand Prix", "Belgium", "VER", 2024),
    ("Italian Grand Prix", "Italy", "VER", 2024),
    ("Japanese Grand Prix", "Japan", "VER", 2024),
    ("Monaco Grand Prix", "Monaco", "VER", 2024),
]


def run_race(driver: str, gp: str, year: int) -> dict:
    pace_agent = PaceAgent()
    timeline_agent = RadioTimelineAgent()

    pace = pace_agent.analyse(driver, gp, year)
    timeline = timeline_agent.build_timeline(driver, gp, year)
    rows = build_rows_from_analysis(driver, gp, year, pace.laps, timeline)

    return {
        "driver": driver,
        "gp": gp,
        "year": year,
        "clean_laps": len([p for p in pace.laps if p.lap_time_s is not None]),
        "radio_labelled_laps": len(timeline),
        "paired_samples": len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--races", type=int, default=len(RACES))
    parser.add_argument("--sleep", type=float, default=1.0)
    args = parser.parse_args()

    summary = []
    for driver, gp, country, year in RACES[: args.races]:
        print(f"Processing {gp} {year} ({driver}) ...", flush=True)
        try:
            result = run_race(driver, gp, year)
            print(f"  {result}", flush=True)
            summary.append(result)
        except Exception as exc:
            print(f"  FAILED: {type(exc).__name__}: {exc}", flush=True)
        time.sleep(args.sleep)

    # Persist whatever we managed to fetch.
    rows: list = []
    for driver, gp, country, year in RACES[: args.races]:
        try:
            pace = PaceAgent().analyse(driver, gp, year)
            timeline = RadioTimelineAgent().build_timeline(driver, gp, year)
            rows.extend(build_rows_from_analysis(driver, gp, year, pace.laps, timeline))
        except Exception:
            continue

    add_samples(rows)

    from app.agents.aggregation import all_samples

    pooled = pooled_causal_analysis(all_samples())
    print("\n=== POOLED RESULT ===")
    for k, v in pooled.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
