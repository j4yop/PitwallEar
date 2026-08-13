"""Shared data models exchanged between agents and the API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Mood = Literal["Calm", "Stressed", "Tired", "Neutral"]


class TranscriptionResult(BaseModel):
    """Output of the transcription agent."""

    text: str
    model: str = ""


class EmotionResult(BaseModel):
    """Output of the emotion agent."""

    mood: Mood
    confidence: float = Field(ge=0.0, le=1.0)
    model: str = ""
    reasoning: str = ""


class LapPoint(BaseModel):
    """One lap-time sample for the pace agent."""

    lap: int
    lap_time_s: float | None = None


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
    source: str = ""


class CorrelationResult(BaseModel):
    """Stress-lap correlation: does mood actually predict pace?

    ``correlation`` is the Pearson coefficient between the per-lap mood score
    (numeric: Calm=1, Neutral=2, Tired=3, Stressed=4) and the lap-time delta
    from the driver's own session mean. ``best_lag`` is the lag (in laps) at
    which mood best predicts pace; a negative lag means mood leads pace (mood
    changes before lap time changes), which is the meaningful direction for an
    early-warning co-driver.
    """

    correlation: float | None = Field(ge=-1.0, le=1.0)
    best_lag: int = 0
    p_value: float | None = None
    sample_size: int
    mood_timeline: list[MoodPoint] = Field(default_factory=list)
    stress_laps: list[LapPoint] = Field(default_factory=list)
    non_stress_laps: list[LapPoint] = Field(default_factory=list)
    reasoning: str = ""


class AnalysisResponse(BaseModel):
    """Complete analysis returned to the frontend."""

    transcription: TranscriptionResult
    emotion: EmotionResult
    pace: PaceResult
    insight: Insight
    agreement: AgreementResult | None = None
    correlation: CorrelationResult | None = None
