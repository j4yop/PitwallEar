# Test coverage gaps: aggregation module + weak math assertions

Status: ready-for-agent

- `app/agents/aggregation.py` has zero tests despite backing /aggregation,
  the headline significance layer. Needs hermetic tests with a tmp-path DB:
  empty-store shape, seeded rows → expected mood_leads_fraction, PK-replace.
- `tests/test_agents.py:40-60`: monotonic fixture only asserts -1<=r<=1;
  should assert r > 0.9. Granger branch never exercised through
  correlate_timeline_to_pace (n=6 always routes to TE).
- Legacy correlate_stress_to_pace untested; agreement 0.75 boundary untested.
- live_stream poll_once dedupe loop untested.

## Comments

## Comments

2026-08-25: Shipped in fix/review-followups - test_aggregation.py covers
empty store, PK-replace, pooled median lead, no-leads n/a regression, and
row building; monotonic correlation fixture now asserts r > 0.9; agreement
0.75 boundary tested; degenerate pearson tested; risk-lead significance
gating tested; bidirectional Granger/TE direction tests added; independent-
series and dof-floor tests added. Still open: live_stream poll_once dedupe.
