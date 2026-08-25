# Guard against NaN Pearson r reaching API responses

Status: resolved

`app/agents/stats.py:42-49`: the only guard is `size < 3`. A constant series
(common: keyword fallback defaults every lap to Neutral) makes pearsonr return
(nan, nan); Pydantic serializes it and clients receive invalid JSON (`NaN`).

Fix: zero-variance check on both inputs before calling pearsonr; return None
and propagate correlation=None through CorrelationResult (schema already
allows nullable).

## Comments

2026-08-25: Fixed — pearson returns (None, None) on degenerate input;
correlate_timeline_to_pace maps that to correlation=None with reasoning.
