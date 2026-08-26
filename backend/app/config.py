"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    """Runtime configuration for the PitwallEar agents.

    Every model id can be overridden with an environment variable so the same
    code runs locally (CPU-safe tiny models) and in production (larger models).
    """

    hf_token: str = field(default_factory=lambda: os.getenv("HF_TOKEN", ""))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "huggingface"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))

    # Speech-to-text. whisper-tiny is small enough to run on a laptop CPU while
    # still producing readable English transcripts for the demo.
    asr_model: str = field(
        default_factory=lambda: os.getenv("ASR_MODEL", "openai/whisper-tiny")
    )

    # Speech-emotion recognition (SUPERB benchmark). This model predicts the
    # eight standard emotion labels and runs on CPU.
    emotion_model: str = field(
        default_factory=lambda: os.getenv(
            "EMOTION_MODEL",
            "superb/wav2vec2-base-superb-er",
        )
    )

    # Text-emotion fallback. Used when the caller provides transcript text
    # instead of audio, or when audio emotion inference is unavailable.
    text_emotion_model: str = field(
        default_factory=lambda: os.getenv(
            "TEXT_EMOTION_MODEL",
            "cardiffnlp/twitter-roberta-base-emotion",
        )
    )

    # LLM for the final synthesis. Both providers are supported through a
    # single interface; the deterministic fallback keeps the demo alive without
    # either.
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")
    )

    # Startup model warm-up: "text" (default), "all" (ASR + audio too), or
    # "none". Memory-constrained hosts (Render free = 512 MB) must use "none":
    # eager loading there OOM-crashes the container into a 503 loop.
    warmup: str = field(
        default_factory=lambda: os.getenv("PITWALLEAR_WARMUP", "text")
    )


settings = Settings()
