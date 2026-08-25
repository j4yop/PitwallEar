# Stop blocking the event loop in /analyse-text and /analyse

Status: resolved

`app/main.py:156` (`analyse_text`) and `app/main.py:190` (`analyse`) are
`async def`, but every downstream call is synchronous and slow (torch
inference, FastF1/OpenF1 downloads, 60s LLM call). One request freezes all
others including /health.

Fix: declare both handlers plain `def` so FastAPI runs them in its threadpool
(the pattern already used by /timeline and /live). For the audio upload, read
via `audio.file.read()` (sync) instead of `await audio.read()`, and enforce a
max upload size while there.

## Comments

2026-08-25: Fixed — both handlers are now sync; audio path reads via
audio.file with a 25 MB cap returning 413.
