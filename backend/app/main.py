"""FastAPI application for PitwallEar."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agents import EmotionAgent, Orchestrator, PaceAgent, TranscriptionAgent
from app.agents.aggregation import (
    all_samples,
    build_rows_from_analysis,
    clear_samples,
    pooled_causal_analysis,
)
from app.agents.explainability import build_explainability
from app.agents.radio_timeline import RadioTimelineAgent
from app.schemas import (
    AnalysisResponse,
    CorrelationResult,
    EmotionResult,
    Explainability,
    Insight,
    LapPoint,
    MoodPoint,
    PaceResult,
    TranscriptionResult,
)

app = FastAPI(title="PitwallEar", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    # Only the Vite dev/preview servers need cross-origin access. The wildcard
    # previously let any webpage hit (and clear) the API.
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy singletons so the API imports without downloading model weights.
_transcription = TranscriptionAgent()
_emotion = EmotionAgent()
_pace = PaceAgent()
_orchestrator = Orchestrator()
_timeline = RadioTimelineAgent(_emotion)


@app.on_event("startup")
def _warm_up_models() -> None:
    """Pre-load the text emotion model so the first /analyse-text request is fast.

    The text pipeline is the one the Demo/Text paths depend on; without a warm-up
    the first request triggers a 30-40s model download/load inside the handler,
    which surfaces as a proxy timeout (502) in the frontend.
    """
    import threading

    # Import transformers fully in the MAIN thread before any worker/warm-up
    # thread touches it: concurrent first-time imports of its lazy module
    # graph can leave a partially-initialized module behind on 3.13
    # ("cannot import name 'pipeline'").
    try:
        import transformers  # noqa: F401
    except Exception:
        pass  # Cache-only cold machines still work through fallbacks.

    def _warm_up() -> None:
        try:
            _emotion._load_text()
        except Exception:
            # Cache-only mode can legitimately fail on a cold machine; the request
            # path will then fall back to the keyword classifier.
            pass

    threading.Thread(target=_warm_up, daemon=True).start()


class TextRequest(BaseModel):
    text: str
    driver: str = "VER"
    gp: str = "Melbourne"
    year: int = 2025


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/timeline", response_model=list[MoodPoint])
def timeline(driver: str = "VER", gp: str = "Melbourne", year: int = 2025) -> list[MoodPoint]:
    """Return the per-lap radio mood timeline for a driver.

    This is the real data the stress-pace correlation consumes. It is exposed
    as its own endpoint so the frontend can render the mood timeline directly,
    and so a judge can inspect the raw per-lap labels.
    """
    return _timeline.build_timeline(driver, gp, year)


@app.get("/demo", response_model=AnalysisResponse)
def demo() -> AnalysisResponse:
    """Return a fully-formed analysis with no model or data calls."""
    transcription = TranscriptionResult(
        text="The rears are gone, mate. I've got no grip into turn three.",
        model="demo",
    )
    audio_emotion = EmotionResult(
        mood="Stressed",
        confidence=0.91,
        model="demo",
        reasoning="Demo sample: dominant tone label 'angry'.",
    )
    text_emotion = EmotionResult(
        mood="Stressed",
        confidence=0.88,
        model="demo",
        reasoning="Demo sample: transcript reads 'grip gone'.",
    )
    pace = PaceResult(
        trend="slowing",
        delta_vs_recent_s=0.42,
        laps=[
            LapPoint(lap=10, lap_time_s=86.1),
            LapPoint(lap=11, lap_time_s=86.4),
            LapPoint(lap=12, lap_time_s=86.9),
            LapPoint(lap=13, lap_time_s=87.3),
            LapPoint(lap=14, lap_time_s=87.8),
        ],
        reasoning="Demo sample: last lap is +0.42s vs the previous four laps.",
    )
    demo_timeline = [
        MoodPoint(lap=10, mood="Calm", confidence=0.8, source="demo"),
        MoodPoint(lap=11, mood="Neutral", confidence=0.7, source="demo"),
        MoodPoint(lap=12, mood="Stressed", confidence=0.6, source="demo"),
        MoodPoint(lap=13, mood="Stressed", confidence=0.85, source="demo"),
        MoodPoint(lap=14, mood="Stressed", confidence=0.9, source="demo"),
    ]

    insight, agreement, correlation = _orchestrator.synthesise(
        transcription, audio_emotion, pace, text_emotion, demo_timeline
    )

    explainability = build_explainability(
        transcription, audio_emotion, pace, agreement, correlation
    )

    return AnalysisResponse(
        transcription=transcription,
        emotion=audio_emotion,
        pace=pace,
        insight=insight,
        agreement=agreement,
        correlation=correlation,
        explainability=explainability,
    )


@app.post("/analyse-text", response_model=AnalysisResponse)
def analyse_text(req: TextRequest) -> AnalysisResponse:
    """Run the co-driver pipeline from a transcript (no audio required).

    Deliberately a sync handler: every downstream call (torch inference,
    FastF1/OpenF1 fetches, the LLM request) is blocking, so FastAPI runs this
    in its threadpool instead of freezing the event loop.
    """
    transcription = TranscriptionResult(text=req.text, model="text-input")
    text_emotion = _emotion.classify_text(req.text)
    pace = _pace.analyse(req.driver, req.gp, req.year)
    timeline = _timeline.build_timeline(req.driver, req.gp, req.year)

    insight, agreement, correlation = _orchestrator.synthesise(
        transcription, text_emotion, pace, text_emotion=None, timeline=timeline
    )

    explainability = build_explainability(
        transcription, text_emotion, pace, agreement, correlation,
        text_emotion=text_emotion,
    )

    # Persist paired samples for the multi-race significance runner.
    build_rows = build_rows_from_analysis(req.driver, req.gp, req.year, pace.laps, timeline)
    if build_rows:
        from app.agents.aggregation import add_samples

        add_samples(build_rows)

    return AnalysisResponse(
        transcription=transcription,
        emotion=text_emotion,
        pace=pace,
        insight=insight,
        agreement=None,
        correlation=correlation,
        explainability=explainability,
    )


_MAX_UPLOAD_BYTES = 25 * 1024 * 1024


@app.post("/analyse", response_model=AnalysisResponse)
def analyse(
    audio: UploadFile = File(...),
    driver: str = Form("VER"),
    gp: str = Form("Melbourne"),
    year: int = Form(2025),
) -> AnalysisResponse:
    """Run the full audio co-driver pipeline on an uploaded radio clip.

    Sync handler for the same reason as /analyse-text. The upload is read via
    the sync file handle with a hard size cap so a huge body cannot exhaust
    memory.
    """
    raw = audio.file.read(_MAX_UPLOAD_BYTES + 1)
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Audio upload exceeds {_MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
        )

    transcription = _transcription.transcribe_bytes(raw)
    audio_emotion = _emotion.classify_bytes(raw)
    text_emotion = _emotion.classify_text(transcription.text)
    pace = _pace.analyse(driver, gp, year)
    timeline = _timeline.build_timeline(driver, gp, year)

    insight, agreement, correlation = _orchestrator.synthesise(
        transcription, audio_emotion, pace, text_emotion, timeline
    )

    explainability = build_explainability(
        transcription, audio_emotion, pace, agreement, correlation
    )

    return AnalysisResponse(
        transcription=transcription,
        emotion=audio_emotion,
        pace=pace,
        insight=insight,
        agreement=agreement,
        correlation=correlation,
        explainability=explainability,
    )


@app.get("/aggregation", response_model=dict)
def aggregation() -> dict:
    """Return the pooled multi-race causal lead-lag result.

    This is the significance layer: it aggregates every persisted paired sample
    and tests whether mood leads pace across the pooled corpus rather than
    relying on a single race's small sample.
    """
    rows = all_samples()
    return pooled_causal_analysis(rows)


@app.post("/aggregation/clear", response_model=dict)
def aggregation_clear() -> dict:
    """Wipe the persistent pooled-sample store.

    Deliberately POST: a GET here could be triggered by prefetch/link-preview
    requests and silently destroy the corpus.
    """
    clear_samples()
    return {"status": "cleared"}


@app.get("/live", response_model=dict)
def live(driver: str = "VER", gp: str = "Melbourne", year: int = 2025) -> dict:
    """Near-real-time replay snapshot for a driver's latest laps."""
    from app.agents.live import live_snapshot

    return live_snapshot(driver, gp, year)


@app.get("/live/stream")
async def live_stream(driver: str = "VER", gp: str = "Melbourne", year: int = 2025):
    """Stream the growing mood timeline as Server-Sent Events.

    Each event is a JSON payload with the mode, new-clip count, and the updated
    timeline. The stream polls OpenF1 every few seconds and emits only when new
    clips arrive. It falls back to a clearly-labelled near-real-time replay when
    the session is not live.
    """
    import asyncio

    from app.agents.live_stream import LiveStreamEngine

    engine = LiveStreamEngine()

    async def event_generator():
        # Emit an initial heartbeat so the client knows the stream is live.
        yield "event: init\ndata: {\"status\":\"streaming\"}\n\n"

        while True:
            try:
                from app.agents.live import live_pace

                pace_data = live_pace(driver, gp, year)
                result = await engine.poll_once(driver, gp, year)
                result["pace"] = pace_data
                result["mode"] = "live" if pace_data["is_live"] else result["mode"]
                yield (
                    "event: update\n"
                    f"data: {json.dumps(result)}\n\n"
                )
            except Exception as exc:
                yield (
                    "event: error\n"
                    f"data: {{\"error\":\"{type(exc).__name__}\"}}\n\n"
                )
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Serve the built React app so the Hugging Face Space is a single process.
# In the Docker image the layout is /app/backend and /app/frontend/dist; in a
# local dev checkout it is PitwallEar/backend and PitwallEar/frontend/dist.
def _resolve_built_app() -> Path | None:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "frontend" / "dist",
        Path("/app/frontend/dist"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


_BUILT_APP = _resolve_built_app()
if _BUILT_APP is not None:
    app.mount("/", StaticFiles(directory=str(_BUILT_APP), html=True), name="app")
