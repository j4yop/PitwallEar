# Honor cache-only mode in TranscriptionAgent

Status: resolved

`app/agents/transcription.py:30-38` promises cache-only-by-default like the
emotion agent, but `_load()` never passes `local_files_only=`. Whisper silently
downloads inside request handlers on cold machines, and a failing download is
retried on every call (no failed latch).

Fix: mirror `EmotionAgent` — pass `local_files_only=not allow_download`, latch
load failures into a labelled RuntimeError.

## Comments

2026-08-25: Fixed.
