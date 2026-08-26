# Smaller correctness fixes queued from review

Status: resolved

Deferred smaller items:
- NaT lap-start slips through hasattr(ts,"total_seconds") guard and misassigns
  clips (radio_timeline.py:103) — use pd.isna().
- Temperature calibration binary-logit formula applied to 4-8 class softmax
  raises confidence below 0.5 (emotion.py:72-84).
- Audio-emotion fallback returns real model id with confidence 0.0 so
  explainability never flags it (emotion.py:157-163) — label "audio-unavailable".
- Transcription failures indistinguishable from silence (transcription.py:48).
- Streamed timeline laps always 0 in /live/stream SSE (live_stream.py:160+).
- LLM calls lack timeout=; HF api-inference 404s for chat models
  (orchestrator.py:127-138) — use router.huggingface.co chat completions.
- Unvalidated driver/gp/year flow into upstream URLs and permanent DB rows.

## Comments

## Comments

2026-08-25 (PR 1): NaT lap-start guard, transcription failure sentinel.
2026-08-25 (PR 2): OpenAI client timeout=15/max_retries=1; HF calls moved to
router.huggingface.co chat completions with timeout=15; audio-emotion
fallback labelled "audio-unavailable" and flagged by explainability;
multi-class calibration via calibrate_from_scores (log-prob temperature
scaling) replacing the binary-logit formula; upstream query params quoted,
year cast to int. Still open: SSE streamed timeline laps always 0;
arbitrary driver/gp/year rows in the aggregation DB (needs an allowlist).
2026-08-25 (round 3): SSE lap alignment DONE - the stream engine fetches
FastF1 lap starts once per session and maps clip timestamps to real laps;
unaligned points are labelled "openf1-live-unaligned" instead of faking a
lap. Aggregation DB allowlist DONE - add_samples rejects unknown driver
codes, out-of-range years, invalid laps and unknown moods (tested). Both
remaining items closed.
