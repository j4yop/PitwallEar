# PitwallEar — The Silent Co-Driver

**A multi-agent AI system that reads a Formula 1 driver's emotional state from
team radio and correlates it with on-track pace — surfacing early warning
signs before they show up in the lap times.**

Built for Hackathon Problem Statement 1: *"The Silent Co-Driver: Reading
Driver Stress from Radio Calls."*

PitwallEar goes beyond transcribe-and-label. Its two novel contributions are a
**cross-model agreement check** (does *how* the driver speaks match *what*
they say?) and a **lagged stress-pace correlation** (does mood change *before*
pace?). The latter is the early-warning property that makes a co-driver
useful, not just descriptive.

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

## The two novel ideas

### 1. Cross-model agreement

A driver can sound calm while describing a serious car problem, or sound
stressed while insisting everything is fine. Comparing the **audio-tone mood**
against the **transcript-text mood** surfaces those mismatches:

- `Agree` — tone and words tell the same story.
- `Disagree` — the driver's words and voice diverge, which is itself a signal
  worth flagging.

### 2. Lagged stress-pace correlation

A single mood label is not actionable. What matters is whether mood **predicts**
pace. PitwallEar aligns a real per-lap mood timeline with lap-time deltas and
searches over a small lag window:

- **Negative lag** → mood changes before pace (early-warning).
- **Positive lag** → pace changes before mood (mood is a response).
- **Zero lag** → they move together.

The result is a Pearson coefficient with a p-value and a best lag, computed on
real data — not a canned "stress detected" sticker.

---

## Architecture

Four specialised agents feed a thin orchestrator:

| Agent | Role | Model (Hugging Face) |
|-------|------|----------------------|
| Transcription | speech → text | `openai/whisper-tiny` |
| Emotion | audio tone or text → mood | `superb/wav2vec2-base-superb-er` (audio) / `cardiffnlp/twitter-roberta-base-emotion` (text) |
| Radio timeline | per-lap radio → mood timeline | text-emotion model applied to OpenF1 radio |
| Pace | lap times → pace trend | FastF1 |
| Orchestrator | fuse agents → co-driver insight | Mistral via HF, or OpenAI |

The orchestrator only synthesises — it does not invent the numbers. Every
metric that drives the call is computed deterministically by the agents and
passed into the prompt verbatim.

---

## Three ways to run

1. **Demo** — `GET /demo` returns a complete analysis with no models, tokens,
   or data calls. Useful for a first look.
2. **Text** — `POST /analyse-text` runs text-emotion + the real radio timeline
   + correlation from a pasted transcript.
3. **Audio** — `POST /analyse` runs full ASR + audio emotion + timeline +
   correlation from an uploaded clip.

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

### Frontend

```bash
cd frontend
npm install --include=dev     # if NODE_ENV=production is set globally
npm run dev
```

Open **http://localhost:5173** and use the **Demo** tab first.

### Environment

Copy `backend/.env.example` to `backend/.env` and set:

```
HF_TOKEN=hf_...
PITWALLEAR_ALLOW_DOWNLOAD=1
```

The token lets the models download with higher rate limits. Without
`PITWALLEAR_ALLOW_DOWNLOAD=1`, models load in cache-only mode and degrade to a
clearly-labelled keyword fallback rather than hanging.

### Full audio + live data

```bash
cd backend
pip install -e ".[audio,pace]"
```

---

## Testing

```bash
cd backend
python -m pytest
```

---

## Stack

- **Backend** — FastAPI, Python 3.10+
- **Frontend** — React + Vite + TypeScript + Recharts
- **Models** — Hugging Face (Whisper, SUPERB, Twitter-RoBERTa, Mistral)
- **Data** — FastF1 (lap times) and OpenF1 (team radio)

---

## Limitations and future work

The pipeline is fully end-to-end on real data, but a single race does not
contain enough radio messages to reach statistical significance for the
stress-pace correlation (typically n < 10 paired laps). This is a data-volume
limitation, not a method limitation.

**Planned improvements:**

1. **Multi-race batch runner** — aggregate mood-vs-pace pairs across many
   drivers and Grands Prix to reach a statistically significant sample.
2. **Streaming audio path** — process a live radio feed instead of a single
   clip.
3. **Per-lap audio alignment** — map each radio clip to its exact lap using
   OpenF1 timestamps rather than a nominal lap-length estimate.
4. **Calibrated emotion confidence** — replace raw model probabilities with
   calibrated scores for the final co-driver call.

---

## Disclaimer

Formula 1, F1 and related marks are trademarks of Formula One Licensing B.V.
and are used for reference only. Race data comes from the public FastF1 and
OpenF1 APIs and is used for educational purposes. This project is not
affiliated with Formula 1, the FIA, or any team.

## Credits

The multi-agent orchestration pattern is inspired by
[F1 StratLab](https://github.com/VforVitorio/F1-StratLab) by Víctor Vega
Sobral. This project targets a different problem (driver stress from radio)
and is an independent implementation.
