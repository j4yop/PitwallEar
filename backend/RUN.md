# Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows (this environment)
# source .venv/bin/activate   # macOS / Linux
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The core install needs no native audio deps. The reliable paths are:

- `GET /demo` — a canned full analysis (no models, no token)
- `POST /analyse-text` — transcript → text-emotion → pace → insight

For full audio (`POST /analyse`), install the audio extra and FastF1:

```bash
pip install -e ".[audio,pace]"
```

Then run the tests:

```bash
python -m pytest
```
