# Declare scipy as a core dependency

Status: resolved

`app/agents/stats.py:44,85,149` imports `scipy.stats`, but `scipy` is absent
from `[project] dependencies` in `backend/pyproject.toml`. It is only pulled in
transitively by the optional `audio`/`pace` extras, so the advertised bare
`pip install -e .` install raises ImportError at runtime on `/analyse-text`.

Fix: add `"scipy>=1.10"` to core dependencies.

## Comments

2026-08-25: Fixed and reinstalled into backend/.venv.
