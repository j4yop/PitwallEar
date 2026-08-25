# Do not cache failed upstream fetches forever

Status: resolved

`app/agents/radio_timeline.py:57-64` and `app/agents/pace.py:27-31` write the
empty result into process-lifetime caches inside the same except block that
handles transient network errors. One timeout poisons (driver, gp, year) until
restart.

Fix: only cache non-empty successes; let transient failures fall through
un-cached so the next request retries.

## Comments

2026-08-25: Fixed in both agents.
