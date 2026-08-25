# Infra cleanup: Dockerfile torch CPU, npm ci, gitignore, pytest.ini

Status: resolved

- Dockerfile:5 uses npm install → switch to npm ci --include=dev; unpinned
  torch pulls CUDA wheels into slim image → add CPU extra index or pin range.
- .gitignore missing *.egg-info/, .DS_Store, .scratch/, backend/.cache/
- pytest.ini:2 testpaths = ["tests"] is broken ini-list syntax → testpaths = tests

## Comments

2026-08-25: pytest.ini and .gitignore fixed. Dockerfile torch pin left as a
follow-up (needs a build to verify image size).
