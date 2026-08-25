# Smaller correctness fixes queued from review

Status: ready-for-agent

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
