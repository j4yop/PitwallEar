# Add CI workflow (tests, typecheck, build)

Status: resolved

.github/workflows/ has only keep-alive.yml. Nothing runs pytest, tsc, or the
Docker build; broken commits ship silently.

Fix: add ci.yml on push/PR:
- backend: pip install -e ".[dev,audio,pace]" && pytest
- frontend: npm ci && npm run build

## Comments

## Comments

2026-08-25: Resolved - .github/workflows/ci.yml runs backend pytest
(CPU torch index) and frontend npm ci + build on push/PR.
