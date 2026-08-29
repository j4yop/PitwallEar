# PitwallEar — Agent Guide

The Silent Co-Driver: a multi-agent F1 radio stress-detection system. FastAPI backend (`backend/app/`) + React/Vite dashboard (`frontend/src/`).

## Commands

```bash
# Run everything (backend :8000 + frontend :5173)
./dev.sh

# Backend only
cd backend && ./.venv/bin/uvicorn app.main:app --reload --port 8000

# Tests (hermetic — models/network stubbed)
cd backend && ./.venv/bin/python -m pytest

# Frontend typecheck + build
cd frontend && npm run build
```

Python venv lives at `backend/.venv` (created from `backend/pyproject.toml`). Config via `backend/.env` (see `.env.example`).

## Conventions

- Backend: Python 3.10+, FastAPI, Pydantic v2 schemas in `app/schemas.py`, one agent per file in `app/agents/`
- Agents degrade gracefully instead of throwing — keep fallbacks labelled and honest
- Frontend: React 18 + TypeScript, marketing landing at `/` (`src/pages/Landing.tsx`, Tailwind v4 + shadcn structure under `src/components/ui/`); original dashboard at `/dashboard` (`src/App.tsx`, legacy CSS in `src/dashboard.css`), Vite dev proxy targets `:8000`

## Agent skills

### Issue tracker

Issues live as local markdown under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` at the repo root (created lazily). See `docs/agents/domain.md`.
