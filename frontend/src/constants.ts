export interface AnalysisResponse {
  transcription: { text: string; model: string };
  emotion: {
    mood: string;
    confidence: number;
    calibrated_confidence: number | null;
    reasoning: string;
  };
  pace: {
    trend: string;
    delta_vs_recent_s: number | null;
    laps: { lap: number; lap_time_s: number | null; lap_start: string | null }[];
    reasoning: string;
  };
  insight: { summary: string; action: string; confidence: number };
  agreement?: {
    agrees: boolean;
    agreement_score: number;
    audio_mood: string;
    text_mood: string;
    reasoning: string;
  } | null;
  correlation?: {
    correlation: number | null;
    best_lag: number;
    p_value: number | null;
    sample_size: number;
    mood_timeline: {
      lap: number;
      mood: string;
      confidence: number;
      calibrated_confidence: number | null;
      transcript: string;
      clip_url: string;
    }[];
    stress_laps: { lap: number; lap_time_s: number | null }[];
    non_stress_laps: { lap: number; lap_time_s: number | null }[];
    reasoning: string;
    causal: {
      method: string;
      statistic: number;
      p_value: number;
      best_lag: number;
      direction: string;
      sample_size: number;
      reasoning: string;
    } | null;
    risk_lead_time_laps: number | null;
    lead_time_confidence: number | null;
  } | null;
  explainability?: {
    transcript: string;
    audio_mood: string | null;
    text_mood: string | null;
    agreement_reason: string;
    pace_reason: string;
    causal_reason: string;
    waveform_available: boolean;
    prosody_features: Record<string, number>;
    failure_modes: string[];
  } | null;
}

export type Mode = "demo" | "text" | "audio" | "live";

export const MOOD_CLASS: Record<string, string> = {
  Calm: "Calm",
  Stressed: "Stressed",
  Tired: "Tired",
  Neutral: "Neutral",
};

export const MODES: Mode[] = ["demo", "text", "audio", "live"];

export const MODE_KEYS: Record<Mode, string> = {
  demo: "1",
  text: "2",
  audio: "3",
  live: "4",
};

export const MODE_LABELS: Record<Mode, string> = {
  demo: "Demo",
  text: "Text",
  audio: "Audio",
  live: "Live",
};

export const MODE_HELP: Record<Mode, string> = {
  demo: "Canned sample — no models or data needed. See the full output instantly.",
  text: "Paste a radio transcript. Runs text emotion + real lap timeline.",
  audio: "Upload a radio clip. Runs speech-to-text + tone + timeline.",
  live: "Stream the growing mood timeline from the active session via Server-Sent Events.",
};

// Shared Recharts theme so the two charts stay visually consistent and the
// inline style objects are not re-created on every render.
export const CHART_COLORS = {
  grid: "#c6ccbb",
  axis: "#5a6152",
  pace: "#1f7a3d",
  baseline: "#878e7c",
  stress: "#c63d2f",
} as const;

export const TOOLTIP_STYLE = {
  background: "#f4f5ef",
  border: "1px solid #aab29b",
  color: "#171b12",
  fontSize: 12,
  fontFamily: "IBM Plex Mono",
} as const;
