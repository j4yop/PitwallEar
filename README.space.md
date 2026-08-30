---
title: PitwallEar - The Silent Co-Driver
emoji: 🎙️
colorFrom: yellow
colorTo: green
sdk: gradio
app_file: app/gradio_app.py
pinned: false
---

# PitwallEar — The Silent Co-Driver

A multi-agent AI system that reads a Formula 1 driver's emotional state from
team radio and correlates it with on-track pace.

Open the **Demo** tab for an instant look, or use **Text**/**Audio** for a live
run.

- **Transcription** — Whisper
- **Emotion** — speech/text emotion models
- **Pace** — FastF1 lap times
- **Radio timeline** — OpenF1 team radio
- **Novel** — cross-model agreement + lagged stress-pace correlation

Set `HF_TOKEN` in the Space secrets to enable real model downloads; without it
the pipeline degrades to a clearly-labelled fallback.

Note: the original Docker-based Space was the previous deployment, this
gradio-based Space is the free-tier friendly variant that runs without a paid
HF PRO subscription. The FastAPI pipeline is unchanged; this Space just
exposes it through a Gradio UI.
