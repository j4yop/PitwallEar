# Unknown driver codes must not silently resolve to Verstappen's radio

Status: resolved

`app/agents/radio_timeline.py:143`: `_driver_number` falls back to
`static.get(driver.upper(), 1)` — car number 1 is VER. Any unmapped driver
(new rookies, year-specific numbers) gets another driver's radio labelled as
theirs, poisoning timelines, correlations, and aggregation rows.

Fix: return None for unmapped drivers and skip clip fetching instead of
guessing.

## Comments

2026-08-25: Fixed — returns None; build_timeline skips with a labelled note.
