"""Shared data models exchanged between agents and the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mood = Literal["Calm", "Stressed", "Tired", "Neutral"]


class TranscriptionResult(BaseModel):
    """Output of the transcription agent."""

    text: str
    model: str = ""
    segments: list[dict] = Field(default_factory=list)


class EmotionResult(BaseModel):
    """Output of the emotion agent."""

    mood: Mood
    confidence: float = Field(ge=0.0, le=1.0)
    calibrated_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    model: str = ""
    reasoning: str = ""


class LapPoint(BaseModel):
    """One lap-time sample for the pace agent."""

    lap: int
    lap_time_s: float | None = None
    lap_start: str | None = None


class PaceResult(BaseModel):
    """Output of the pace agent."""

    trend: str
    delta_vs_recent_s: float | None = None
    laps: list[LapPoint] = Field(default_factory=list)
    reasoning: str = ""


class Insight(BaseModel):
    """Final co-driver insight produced by the orchestrator."""

    summary: str
    action: str
    confidence: float = Field(ge=0.0, le=1.0)


class AgreementResult(BaseModel):
    """Cross-model agreement between audio tone and transcript emotion."""

    agrees: bool
    agreement_score: float = Field(ge=0.0, le=1.0)
    audio_mood: Mood
    text_mood: Mood
    reasoning: str = ""


class MoodPoint(BaseModel):
    """One per-lap emotion reading, aligned to a lap number."""

    lap: int
    mood: Mood
    confidence: float = Field(ge=0.0, le=1.0)
    calibrated_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source: str = ""
    transcript: str = ""
    clip_url: str = ""


class CausalResult(BaseModel):
    """Causal lead-lag analysis: does mood actually lead pace?"""

    method: str
    statistic: float
    p_value: float
    best_lag: int
    direction: str
    sample_size: int
    reasoning: str


class CorrelationResult(BaseModel):
    """Stress-lap correlation with causal lead-lag and calibration.

    ``correlation`` is the Pearson coefficient between the per-lap mood score
    (numeric: Calm=1, Neutral=2, Tired=3, Stressed=4) and the lap-time delta
    from the driver's own session mean. ``best_lag`` is the lag (in laps) at
    which mood best predicts pace; a negative lag means mood leads pace (mood
    changes before lap time changes), which is the meaningful direction for an
    early-warning co-driver. ``causal`` carries the Granger/transfer-entropy
    result and ``risk_lead_time_laps`` is the lead-time headline metric.
    """

    correlation: float | None = Field(default=None, ge=-1.0, le=1.0)
    best_lag: int = 0
    p_value: float | None = None
    sample_size: int = 0
    mood_timeline: list[MoodPoint] = Field(default_factory=list)
    stress_laps: list[LapPoint] = Field(default_factory=list)
    non_stress_laps: list[LapPoint] = Field(default_factory=list)
    reasoning: str = ""
    causal: CausalResult | None = None
    risk_lead_time_laps: int | None = None
    lead_time_confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class Explainability(BaseModel):
    """Human-inspectable artifacts backing every signal."""

    transcript: str = ""
    audio_mood: Mood | None = None
    text_mood: Mood | None = None
    agreement_reason: str = ""
    pace_reason: str = ""
    causal_reason: str = ""
    waveform_available: bool = False
    prosody_features: dict = Field(default_factory=dict)
    failure_modes: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    """Complete analysis returned to the frontend."""

    transcription: TranscriptionResult
    emotion: EmotionResult
    pace: PaceResult
    insight: Insight
    agreement: AgreementResult | None = None
    correlation: CorrelationResult | None = None
    explainability: Explainability | None = None
