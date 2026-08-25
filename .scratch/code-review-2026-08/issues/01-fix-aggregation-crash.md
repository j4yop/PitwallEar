# Fix /aggregation 500 crash when no race shows mood-leads

Status: resolved

`app/agents/aggregation.py:158` sets `median_lead = None` when `lead_laps` is
empty (i.e. at least one race had enough samples but none showed mood leading).
Line 168 then formats `f"{median_lead:.1f}"` → `TypeError: unsupported format
string passed to NoneType` → HTTP 500 on the pooled-significance endpoint.

Fix: guard the f-string the same way line 165 guards `round()`.

## Comments

2026-08-25: Fixed — `median_txt` precomputed with n/a fallback.
