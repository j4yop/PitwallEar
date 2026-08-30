"""Hugging Face Space entrypoint — wraps the existing FastAPI pipeline in a
Gradio UI so the project can be hosted on HF Spaces (free) without Docker.

The Python pipeline under app/agents/ and app/main.py is unchanged; this
file just exposes a simple Demo/Text/Audio interface that calls the same
endpoints the React dashboard would.

To run locally: `gradio app/gradio_app.py` (or `python -m gradio app.gradio_app`).
On HF Spaces: configured via README.space.md (sdk: gradio).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Make the `app` package importable when Gradio runs this file directly.
_BACKEND_DIR = Path(__file__).resolve().parent
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

import gradio as gr
from app.main import app as fastapi_app  # noqa: E402  (imports FastAPI app)
from fastapi.testclient import TestClient  # noqa: E402

# We use FastAPI's TestClient so we hit the *same* endpoints the React
# dashboard calls, with the same agents, fallback behaviour, and schemas.
# No separate code path: the Gradio UI is a thin shell.
_client = TestClient(fastapi_app)


def _render_result(result: dict) -> str:
    """Pretty-print an analysis result as a readable summary."""
    if "error" in result:
        return f"### Error\n\n```\n{result['error']}\n```"

    lines: list[str] = []
    if "transcription" in result and result["transcription"]:
        lines.append(f"### Transcript\n\n> {result['transcription'].get('text', '')}")
    if "emotion" in result and result["emotion"]:
        e = result["emotion"]
        lines.append(
            f"### Emotion\n\n**{e.get('mood', '?')}** "
            f"(conf {e.get('confidence', 0):.2f})\n\n"
            f"_{e.get('reasoning', '')}_"
        )
    if "agreement" in result and result["agreement"]:
        a = result["agreement"]
        verdict = "AGREE" if a.get("agrees") else "DISAGREE"
        lines.append(
            f"### Cross-model agreement\n\n"
            f"**{verdict}** (score {a.get('agreement_score', 0):.2f})\n\n"
            f"- audio: `{a.get('audio_mood')}`\n- text: `{a.get('text_mood')}`"
        )
    if "pace" in result and result["pace"]:
        p = result["pace"]
        lines.append(
            f"### Pace\n\nTrend: **{p.get('trend')}** "
            f"(Δ {p.get('delta_vs_recent_s', '?')}s vs session mean)"
        )
    if "correlation" in result and result["correlation"]:
        c = result["correlation"]
        lead = c.get("risk_lead_time_laps")
        lag = c.get("best_lag")
        f_stat = c.get("granger_f", "?")
        p_val = c.get("granger_p_value", "?")
        lead_str = f"mood leads pace by {lead} lap(s)" if lead is not None else f"best lag = {lag}"
        lines.append(
            f"### Causal lead-lag\n\n{lead_str}\n\n"
            f"Granger F = {f_stat}, p = {p_val}\n\n"
            f"_{c.get('reasoning', '')}_"
        )
    if "insight" in result and result["insight"]:
        ins = result["insight"]
        lines.append(
            f"### Co-driver call\n\n**{ins.get('action', '')}**\n\n"
            f"{ins.get('summary', '')}\n\n"
            f"_(confidence {ins.get('confidence', 0):.2f})_"
        )
    if "explainability" in result and result["explainability"]:
        ex = result["explainability"]
        failures = ex.get("failure_modes", []) or []
        if failures:
            lines.append("### Honest failure modes\n\n" + "\n".join(f"- {f}" for f in failures))

    return "\n\n---\n\n".join(lines) if lines else "_(no result)_"


def _run_demo() -> tuple[str, str]:
    """Call /demo. No setup, no model downloads."""
    r = _client.get("/demo")
    r.raise_for_status()
    result = r.json()
    return _render_result(result), json.dumps(result, indent=2)


def _run_text(text: str, driver: str, gp: str, year: int) -> tuple[str, str]:
    """Call /analyse-text. Text emotion + OpenF1 radio timeline + FastF1 pace."""
    r = _client.post(
        "/analyse-text",
        json={"text": text, "driver": driver, "gp": gp, "year": year},
    )
    r.raise_for_status()
    result = r.json()
    return _render_result(result), json.dumps(result, indent=2)


def _run_audio(audio_path: str | None, driver: str, gp: str, year: int) -> tuple[str, str]:
    """Call /analyse. Full pipeline: Whisper ASR + dual emotion + correlation."""
    if not audio_path:
        return "Upload a radio clip first.", ""
    with open(audio_path, "rb") as f:
        r = _client.post(
            "/analyse",
            files={"audio": (os.path.basename(audio_path), f, "audio/wav")},
            data={"driver": driver, "gp": gp, "year": str(year)},
        )
    r.raise_for_status()
    result = r.json()
    return _render_result(result), json.dumps(result, indent=2)


# ---- UI ----

with gr.Blocks(
    title="PitwallEar — The Silent Co-Driver",
    theme=gr.themes.Soft(primary_hue="red"),
) as demo:
    gr.Markdown(
        """
        # 🎙️ PitwallEar — The Silent Co-Driver

        A multi-agent AI system that reads a Formula 1 driver's emotional state
        from team radio and correlates it with on-track pace.

        **Start with Demo** — canned analysis, no setup, no model downloads.
        """
    )

    with gr.Tabs():
        with gr.TabItem("Demo"):
            gr.Markdown(
                "_Canned sample — renders the full pipeline instantly. "
                "No models loaded, no API keys needed._"
            )
            demo_btn = gr.Button("Run demo", variant="primary")
            demo_md = gr.Markdown()
            demo_json = gr.Code(label="Raw response", language="json")

        with gr.TabItem("Text"):
            with gr.Row():
                text_in = gr.Textbox(
                    label="Radio transcript",
                    lines=3,
                    placeholder="Paste what the driver said over team radio…",
                    value="The rears are gone, mate. I've got no grip into turn three.",
                )
            with gr.Row():
                text_driver = gr.Textbox(label="Driver", value="VER", scale=1)
                text_gp = gr.Textbox(label="Grand Prix", value="Melbourne", scale=2)
                text_year = gr.Number(label="Season", value=2025, precision=0, scale=1)
            text_btn = gr.Button("Analyse text", variant="primary")
            text_md = gr.Markdown()
            text_json = gr.Code(label="Raw response", language="json")

        with gr.TabItem("Audio"):
            gr.Markdown(
                "_Upload a radio clip. Runs Whisper ASR + speech emotion + text "
                "emotion + the per-lap correlation. May take 30–60s on first use._"
            )
            audio_in = gr.Audio(label="Radio clip", type="filepath")
            with gr.Row():
                audio_driver = gr.Textbox(label="Driver", value="VER", scale=1)
                audio_gp = gr.Textbox(label="Grand Prix", value="Melbourne", scale=2)
                audio_year = gr.Number(label="Season", value=2025, precision=0, scale=1)
            audio_btn = gr.Button("Analyse audio", variant="primary")
            audio_md = gr.Markdown()
            audio_json = gr.Code(label="Raw response", language="json")

    demo_btn.click(_run_demo, outputs=[demo_md, demo_json])
    text_btn.click(
        _run_text,
        inputs=[text_in, text_driver, text_gp, text_year],
        outputs=[text_md, text_json],
    )
    audio_btn.click(
        _run_audio,
        inputs=[audio_in, audio_driver, audio_gp, audio_year],
        outputs=[audio_md, audio_json],
    )


if __name__ == "__main__":
    # Local dev: `python app/gradio_app.py`
    demo.queue(max_size=8).launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")))
