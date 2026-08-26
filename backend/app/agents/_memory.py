"""Shared model-memory helpers.

Render's free tier caps containers at 512 MB. Full-precision transformer
weights (RoBERTa-base ≈ 500 MB fp32) blow through that the moment an analysis
loads them, killing the container mid-request — which looks exactly like a
random 502/503. Dynamic int8 quantization shrinks Linear layers ~4x with
negligible accuracy loss for classification, making inference viable there.
"""

from __future__ import annotations

import os


def quantize_enabled() -> bool:
    return os.getenv("PITWALLEAR_QUANTIZE", "0") == "1"


def maybe_quantize_pipeline(pipeline_obj):
    """Int8-quantize a transformers pipeline's torch model in place.

    No-op unless PITWALLEAR_QUANTIZE=1, and falls back to the unquantized
    model on any failure — this must never be the reason a request dies.
    """
    if not quantize_enabled():
        return pipeline_obj
    try:
        import torch

        model = getattr(pipeline_obj, "model", None)
        if model is not None:
            pipeline_obj.model = torch.quantization.quantize_dynamic(
                model, {torch.nn.Linear}, dtype=torch.qint8
            )
    except Exception:
        pass
    return pipeline_obj
