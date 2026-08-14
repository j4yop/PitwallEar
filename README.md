# PitwallEar — The Silent Co-Driver

**A multi-agent AI system that reads a Formula 1 driver's emotional state from
team radio and correlates it with on-track pace — surfacing early warning signs
before they show up in the lap times.**

Built for Hackathon Problem Statement 1: *"The Silent Co-Driver: Reading Driver
Stress from Radio Calls."*

PitwallEar goes beyond transcribe-and-label. Its three novel contributions are:

1. **Cross-model agreement** — does *how* the driver speaks match *what* they
   say?
2. **Causal lead-lag inference** — does mood change *before* pace, tested with
   Granger causality and transfer entropy, not just Pearson correlation?
3. **A pooled significance layer** — aggregating paired mood-vs-pace samples
   across many races so the early-warning claim is *demonstrated*, not just
   theoretical.

The result is a co-driver that reports a **risk lead-time** ("we detect stress N
laps before a pace drop") with calibrated confidence and an honest list of where
the analysis could be wrong.

---

## Table of contents

- [What it does](#what-it-does)
- [Why it matters](#why-it-matters)
- [The two novel ideas](#the-two-novel-ideas)
- [Architecture](#architecture)
- [Pipeline](#pipeline)
- [Run modes](#run-modes)
- [Quick start](#quick-start)
- [API reference](#api-reference)
- [Project structure](#project-structure)
- [Tech stack](#tech-stack)
- [Testing](#testing)
- [Deployment](#deployment)
- [Limitations and future work](#limitations-and-future-work)

---

## What it does

Upload a radio clip, paste a transcript, or run the canned demo. The system:

1. **Transcribes** speech to text (Whisper).
2. **Reads the tone** — audio tone or transcript emotion — and labels it
   `Calm`, `Stressed`, `Tired`, or `Neutral`.
3. **Builds a per-lap mood timeline** from the driver's real radio messages
   across the race.
4. **Pulls real lap times** from FastF1 and computes a Pearson correlation
   between mood and pace, including a lag search to determine whether mood
   *leads* pace (early warning) or merely responds to it.
5. **Synthesises a co-driver call** in plain English: what the pit wall should
   actually do.

The dashboard shows the transcript, mood badge, cross-model agreement, lap-time
chart, stress-vs-baseline pace chart, the per-lap mood timeline, and the
headline correlation with its p-value and lag.

---

## Why it matters

A modern F1 team already has telemetry for pace, tires, brakes, and fuel. What
it lacks is a reliable read on the **human sensor** in the car — the driver.
Stress, fatigue, and frustration show up in the voice before they show up in
sector times. PitwallEar turns that intuition into a measurable signal:

- Does the driver's mood **predict** a pace drop, or only react to it?
- Is the driver masking a real problem with a calm voice?
- When should the pit wall intervene, and why?

---

## The three novel ideas

### 1. Cross-model agreement

A driver can sound calm while describing a serious car problem, or sound
stressed while insisting everything is fine. Comparing the **audio-tone mood**
against the **transcript-text mood** surfaces those mismatches:

- `Agree` — tone and words tell the same story.
- `Disagree` — the driver's words and voice diverge, which is itself a signal
  worth flagging.

The agreement score is a distance-weighted match between the two mood labels,
with a confidence floor so low-confidence readings never masquerade as strong
agreement.

### 2. Causal lead-lag inference

A single mood label is not actionable. What matters is whether mood **causes**
pace changes or merely reacts to them. PitwallEar aligns a real per-lap mood
timeline with lap-time deltas (computed from the driver's own session mean, so
circuit and compound baselines are removed) and runs two causal tests:

- **Granger causality** — does the driver's mood history improve prediction of
  pace beyond pace's own history?
- **Transfer entropy** — does knowing the driver's mood reduce uncertainty about
  pace, without assuming linearity?

The output is a **risk lead-time**: how many laps before a pace change the
signal appears, with a calibrated confidence. A negative lag means mood leads
pace (early-warning); a positive lag means mood is a response.

### 3. Pooled multi-race significance

A single race rarely has enough radio-labelled laps for statistical significance
(typically `n < 10`). PitwallEar persists every paired mood-vs-pace sample in a
SQLite store and runs the causal analysis on the **pooled corpus** across many
drivers and Grands Prix. That turns a single-race anecdote into a demonstrated
result with real sample sizes.

### Honest explainability

Every signal ships with the evidence behind it: the transcript, the audio/text
moods, the agreement reasoning, the pace reasoning, the causal reasoning, and a
self-aware list of failure modes (domain mismatch, small sample, low calibrated
confidence, unavailable data). The co-driver is auditable, not a black box.

The result is a Pearson coefficient with a two-sided p-value and a best lag,
computed on real data — not a canned "stress detected" sticker.

---

## Architecture

Four specialised agents feed a thin orchestrator:

| Agent | Role | Model / source |
|-------|------|----------------|
| Transcription | speech → text | `openai/whisper-tiny` |
| Emotion | audio tone → mood | `superb/wav2vec2-base-superb-er` |
| Emotion | transcript text → mood | `cardiffnlp/twitter-roberta-base-emotion` |
| Radio timeline | per-lap radio → mood timeline | OpenF1 radio + text emotion |
| Pace | lap times → pace trend | FastF1 |
| Orchestrator | fuse agents → co-driver insight | Mistral via HF, or OpenAI |

The orchestrator only synthesises — it does not invent the numbers. Every
metric that drives the call is computed deterministically by the agents and
passed into the prompt verbatim.

```
radio audio ──► Transcription ──► text ──► Emotion (text)
      │                                      │
      └──────────► Emotion (audio)           │
                       │                     │
                       ▼                     ▼
                 Cross-model agreement ◄─────┘
                       │
OpenF1 radio ──► Radio timeline ──► per-lap mood timeline
FastF1 laps ──► Pace agent ───────► lap-time deltas
                       │                     │
                       ▼                     ▼
                 Lagged stress-pace correlation
                       │
                       ▼
                 Orchestrator ──► co-driver call
```

---

## Pipeline

The end-to-end flow for a live audio analysis:

1. **ASR** transcribes the uploaded clip with Whisper.
2. **Audio emotion** classifies the raw waveform into a mood.
3. **Text emotion** classifies the transcript into a mood.
4. **Agreement** compares the two moods and scores their alignment.
5. **Radio timeline** downloads the driver's real radio clips for the session
   from OpenF1, transcribes each, labels it, and collapses to one mood per lap
   (conservatively keeping the most negative label).
6. **Pace** loads the driver's clean lap times from FastF1 and computes
   lap-time deltas from the session mean.
7. **Correlation** aligns the mood timeline to the pace deltas and searches
   lags `-3 … +3` for the best mood-leading-pace relationship.
8. **Orchestrator** feeds all of that into an LLM prompt and produces a
   2–3 sentence pit-wall note plus a recommended action.

If any model or data source is unavailable, the system degrades gracefully
rather than failing: a clearly-labelled keyword fallback for emotion, an empty
timeline for radio, an empty trend for pace, and a deterministic summary when
the LLM is unreachable.

---

## Run modes

| Mode | Endpoint | What it runs |
|------|----------|--------------|
| Demo | `GET /demo` | A complete canned analysis — no models, tokens, or data calls. |
| Text | `POST /analyse-text` | Text emotion + real radio timeline + correlation from a pasted transcript. |
| Audio | `POST /analyse` | Full ASR + audio emotion + timeline + correlation from an uploaded clip. |

The frontend exposes all three as tabs: **Demo**, **Text**, and **Audio**.
Start with Demo — it renders the entire UI instantly.

---

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

The core install needs no native audio dependencies. The reliable paths are
`GET /demo` and `POST /analyse-text`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** and use the **Demo** tab first. The Vite dev
server proxies API calls to the backend on `http://localhost:8000`.

### Environment

Copy `backend/.env.example` to `backend/.env` and set:

```
HF_TOKEN=hf_...
PITWALLEAR_ALLOW_DOWNLOAD=1
```

- `HF_TOKEN` lets the models download with higher rate limits.
- Without `PITWALLEAR_ALLOW_DOWNLOAD=1`, models load in cache-only mode and
  degrade to a clearly-labelled fallback rather than hanging.
- `LLM_PROVIDER` switches the orchestrator between `huggingface` (default) and
  `openai`. Every model id is also overridable via `ASR_MODEL`,
  `EMOTION_MODEL`, `TEXT_EMOTION_MODEL`, and `LLM_MODEL`.

### Full audio + live data

```bash
cd backend
pip install -e ".[audio,pace]"
```

`audio` adds sound decoding (librosa, soundfile); `pace` adds FastF1 for real
lap times.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness check. |
| `GET` | `/demo` | Canned end-to-end analysis. |
| `GET` | `/timeline` | Per-lap radio mood timeline for a driver (query: `driver`, `gp`, `year`). |
| `POST` | `/analyse-text` | Text-only pipeline. Body: `{ text, driver, gp, year }`. |
| `POST` | `/analyse` | Audio pipeline. Multipart: `audio`, `driver`, `gp`, `year`. |
| `GET` | `/aggregation` | Pooled multi-race causal lead-lag result. |
| `GET` | `/aggregation/clear` | Clear the persistent aggregation store. |
| `GET` | `/live` | Near-real-time replay snapshot for a driver's latest laps. |

All analysis endpoints return an `AnalysisResponse` with `transcription`,
`emotion` (with calibrated confidence), `pace`, `insight`, optional `agreement`,
optional `correlation` (with causal lead-lag and risk lead-time), and an
`explainability` artifact.

---

## Project structure

```
PitwallEar/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   │   ├── transcription.py      # Whisper ASR
│   │   │   ├── emotion.py            # audio + text emotion
│   │   │   ├── radio_timeline.py     # OpenF1 radio → mood timeline
│   │   │   ├── pace.py               # FastF1 lap times → pace trend
│   │   │   ├── agreement.py          # cross-model agreement
│   │   │   ├── correlation.py        # lagged stress-pace correlation
│   │   │   └── orchestrator.py       # fusion + co-driver synthesis
│   │   ├── config.py                 # env-driven settings
│   │   ├── schemas.py                # Pydantic response models
│   │   └── main.py                   # FastAPI app + static frontend mount
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx                   # single-page dashboard
│   │   ├── index.css
│   │   └── main.tsx
│   ├── vite.config.ts                # dev proxy to :8000
│   └── package.json
├── Dockerfile                        # multi-stage: Node build → FastAPI serve
├── render.yaml                       # Render deployment config
├── README.space.md                   # Hugging Face Space metadata
└── .env.example
```

---

## Tech stack

- **Backend** — FastAPI, Python 3.10+
- **Frontend** — React 18 + Vite + TypeScript + Recharts
- **Models** — Hugging Face (Whisper, SUPERB wav2vec2, Twitter-RoBERTa, Mistral)
- **Data** — FastF1 (lap times) and OpenF1 (team radio)
- **Deployment** — Docker (single process: FastAPI serves the built React app)

---

## Testing

```bash
cd backend
python -m pytest
```

The test suite covers the agent logic (emotion mapping, agreement scoring,
correlation math) and the API endpoints, with model/network calls stubbed so
tests run hermetically.

---

## Deployment

The `Dockerfile` is a multi-stage build: Node compiles the React app, then
FastAPI serves the static bundle alongside the API on a single port. This makes
PitwallEar a one-process deployment with no separate frontend server.

- **Hugging Face Space** — `README.space.md` is the Space card; the Docker SDK
  runs the image and exposes the app on port `7860`.
- **Render** — `render.yaml` is a ready web-service definition with a
  `/health` check.

Build and run locally:

```bash
docker build -t pitwallear .
docker run -p 7860:7860 -e HF_TOKEN=hf_... -e PITWALLEAR_ALLOW_DOWNLOAD=1 pitwallear
```

Open **http://localhost:7860**.

---

## Limitations and future work

The single-race sample-size limitation has been addressed with a persistent
multi-race aggregation layer (`/aggregation`), which pools every paired
mood-vs-pace sample across drivers and Grands Prix before running the causal
test.

Live mode is a hybrid:

- **Live pace** — sourced from FastF1, which reads F1's official live timing
  data and refreshes during an active session.
- **Radio audio** — near-real-time replay of the most recent complete session.
  OpenF1's *live* audio tier is sponsor-gated; the free tier serves historical
  data. The streaming endpoint labels this explicitly rather than pretending
  the audio is live when it is not.

Remaining limitations:

1. **Live radio audio** — true mid-race radio ingestion requires OpenF1's
   sponsor tier (live REST/MQTT/WebSocket). The current path is the honest
   near-real-time fallback.
2. **Calibration quality** — emotion confidence uses a fixed temperature
   scaling, which is a documented approximation. A fitted per-model calibration
   would require a labelled validation set of in-car radio clips.
3. **Emotion model domain** — the speech-emotion model was not trained on
   engine-noise radio; domain mismatch remains a source of error that the
   explainability panel flags rather than hides.

---

## Disclaimer

Formula 1, F1 and related marks are trademarks of Formula One Licensing B.V.
and are used for reference only. Race data comes from the public FastF1 and
OpenF1 APIs and is used for educational purposes. This project is not
affiliated with Formula 1, the FIA, or any team.
