# Add CI workflow (tests, typecheck, build)

Status: ready-for-agent

.github/workflows/ has only keep-alive.yml. Nothing runs pytest, tsc, or the
Docker build; broken commits ship silently.

Fix: add ci.yml on push/PR:
- backend: pip install -e ".[dev,audio,pace]" && pytest
- frontend: npm ci && npm run build

## Comments
