import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface AnalysisResponse {
  transcription: { text: string; model: string };
  emotion: { mood: string; confidence: number; reasoning: string };
  pace: {
    trend: string;
    delta_vs_recent_s: number | null;
    laps: { lap: number; lap_time_s: number | null }[];
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
    mood_timeline: { lap: number; mood: string; confidence: number }[];
    stress_laps: { lap: number; lap_time_s: number | null }[];
    non_stress_laps: { lap: number; lap_time_s: number | null }[];
    reasoning: string;
  } | null;
}

type Mode = "demo" | "text" | "audio";

const MOOD_CLASS: Record<string, string> = {
  Calm: "Calm",
  Stressed: "Stressed",
  Tired: "Tired",
  Neutral: "Neutral",
};

const MODE_KEYS: Record<Mode, string> = {
  demo: "1",
  text: "2",
  audio: "3",
};

const MODE_HELP: Record<Mode, string> = {
  demo: "Canned sample — no models or data needed. See the full output instantly.",
  text: "Paste a radio transcript. Runs text emotion + real lap timeline.",
  audio: "Upload a radio clip. Runs speech-to-text + tone + timeline.",
};

export default function App() {
  const [mode, setMode] = useState<Mode>("demo");
  const [audio, setAudio] = useState<File | null>(null);
  const [text, setText] = useState(
    "The rears are gone, mate. I've got no grip into turn three."
  );
  const [driver, setDriver] = useState("VER");
  const [gp, setGp] = useState("Melbourne");
  const [year, setYear] = useState(2025);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    setResult(null);
    try {
      if (mode === "demo") {
        const res = await fetch("/demo");
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        setResult(await res.json());
        return;
      }
      if (mode === "text") {
        const res = await fetch("/analyse-text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, driver, gp, year }),
        });
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        setResult(await res.json());
        return;
      }
      if (!audio) return;
      const form = new FormData();
      form.append("audio", audio);
      form.append("driver", driver);
      form.append("gp", gp);
      form.append("year", String(year));
      const res = await fetch("/analyse", { method: "POST", body: form });
      if (!res.ok) throw new Error(`Request failed: ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const lapData = useMemo(
    () =>
      (result?.pace.laps ?? [])
        .filter((p) => p.lap_time_s != null)
        .map((p) => ({ lap: p.lap, time: p.lap_time_s })),
    [result]
  );

  const correlationData = useMemo(() => {
    const baseline = (result?.correlation?.non_stress_laps ?? [])
      .filter((p) => p.lap_time_s != null)
      .map((p) => ({ lap: p.lap, baseline: p.lap_time_s, stress: null }));
    const stressed = (result?.correlation?.stress_laps ?? [])
      .filter((p) => p.lap_time_s != null)
      .map((p) => ({ lap: p.lap, baseline: null, stress: p.lap_time_s }));
    return [...baseline, ...stressed].sort((a, b) => a.lap - b.lap);
  }, [result]);

  const timelineData = useMemo(
    () => (result?.correlation?.mood_timeline ?? []).slice().sort((a, b) => a.lap - b.lap),
    [result]
  );

  const heroValue =
    result?.correlation?.correlation == null
      ? "—"
      : result.correlation.correlation.toFixed(2);

  const heroLag =
    result?.correlation?.best_lag != null && result.correlation.best_lag !== 0
      ? `Mood leads pace by ${Math.abs(result.correlation.best_lag)} lap${
          Math.abs(result.correlation.best_lag) === 1 ? "" : "s"
        }`
      : "Mood and pace aligned";

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            PITWALL<span>EAR</span>
          </div>
          <div className="brand-tag">Race Engineer Co-Pilot</div>
        </div>
        <div className="live-chip">
          <span className="live-dot" />
          {result ? "Analysis complete" : "Ready"}
        </div>
      </header>

      <div className="control-deck">
        <div className="mode-stack">
          {(["demo", "text", "audio"] as Mode[]).map((m) => (
            <button
              key={m}
              className={`mode-tab ${mode === m ? "active" : ""}`}
              onClick={() => setMode(m)}
            >
              {m === "demo" ? "Demo" : m === "text" ? "Text" : "Audio"}
              <span className="kbd">{MODE_KEYS[m]}</span>
            </button>
          ))}
          <div className="mode-help">{MODE_HELP[mode]}</div>
        </div>

        <div className="input-grid">
          {mode === "text" && (
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label>Radio transcript</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={3}
                placeholder="Paste what the driver said over team radio…"
              />
            </div>
          )}

          {mode === "audio" && (
            <label className="drop-zone" style={{ gridColumn: "1 / -1" }}>
              <input
                type="file"
                accept="audio/*"
                onChange={(e) => setAudio(e.target.files?.[0] ?? null)}
              />
              {audio ? audio.name : "Drop radio audio or click to upload"}
            </label>
          )}

          <div className="field">
            <label>Driver</label>
            <input
              value={driver}
              onChange={(e) => setDriver(e.target.value)}
              placeholder="VER"
            />
          </div>
          <div className="field">
            <label>Grand Prix</label>
            <input
              value={gp}
              onChange={(e) => setGp(e.target.value)}
              placeholder="Melbourne"
            />
          </div>
          <div className="field">
            <label>Season</label>
            <input
              type="number"
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              placeholder="2025"
            />
          </div>
          <div className="field">
            <label>&nbsp;</label>
            <span className="mono-note">
              Driver, GP and season pull the pace and radio timeline from FastF1.
            </span>
          </div>
        </div>

        <button
          className="fire-btn"
          onClick={run}
          disabled={loading || (mode === "audio" && !audio)}
        >
          {loading ? "Analysing…" : "Run analysis →"}
        </button>
      </div>

      {error && (
        <div className="panel" style={{ marginBottom: 16, padding: 12 }}>
          <span style={{ color: "var(--red)" }}>{error}</span>
        </div>
      )}

      {!result && !loading && (
        <div className="hero">
          <div className="hero-metric primary">
            <span className="label">Signal ready</span>
            <span className="value">—</span>
            <span className="unit">
              Choose Demo to see the full pipeline with canned data, or Text/Audio
              for a live run.
            </span>
          </div>
          <div className="panel">
            <div className="panel-head">
              <h2>What this does</h2>
            </div>
            <div className="panel-body">
              <p className="mono-note">
                PitwallEar reads a radio message, labels the driver's tone, aligns
                it to a per-lap mood timeline, and correlates that timeline with
                pace. The headline metric is the stress-pace correlation and its
                lag — mood leading pace is the early-warning signal a race
                engineer actually needs.
              </p>
            </div>
          </div>
        </div>
      )}

      {result && (
        <>
          <div className="hero">
            <div className={`hero-metric ${result.emotion.mood === "Calm" ? "calm" : result.emotion.mood === "Tired" ? "tired" : "stress"}`}>
              <span className="label">Driver tone</span>
              <span className="value">{result.emotion.mood}</span>
              <span className="unit">
                {(result.emotion.confidence * 100).toFixed(0)}% confidence
              </span>
              <span className="caption">
                The mood detected from the radio clip — tone of voice (audio) or
                word choice (text).
              </span>
            </div>

            <div className="hero-metric primary">
              <span className="label">Stress → pace correlation</span>
              <span className="value">{heroValue}</span>
              <span className="unit">{heroLag}</span>
              <span className="caption">
                How strongly the per-lap mood predicts lap time. Values near ±1 are
                strong; the lag tells you whether mood changes before pace.
              </span>
            </div>
          </div>

          {result.agreement && (
            <div className="panel" style={{ marginBottom: 16 }}>
              <div className="panel-head">
                <h2>Cross-model agreement</h2>
                <span
                  className={`agreement-badge ${result.agreement.agrees ? "agree" : "disagree"}`}
                >
                  {result.agreement.agrees ? "Agree" : "Disagree"}{" "}
                  {(result.agreement.agreement_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="panel-body">
                <p className="mono-note">
                  Audio tone: {result.agreement.audio_mood} · Transcript:{" "}
                  {result.agreement.text_mood}
                </p>
                <p className="mono-note">{result.agreement.reasoning}</p>
                <p className="caption">
                  Compares <em>how</em> the driver says it (tone) with{" "}
                  <em>what</em> they say (words). A calm voice describing a serious
                  problem is a disagreement worth flagging.
                </p>
              </div>
            </div>
          )}

          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h2>Transcript</h2>
              </div>
              <div className="panel-body">
                <p className="insight-quote">
                  {result.transcription.text || "(empty)"}
                </p>
                <p className="caption">
                  The speech-to-text output for the uploaded or pasted radio
                  message.
                </p>
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>Co-driver call</h2>
              </div>
              <div className="panel-body">
                <p className="insight-quote">{result.insight.summary}</p>
                <div className="action-call">{result.insight.action}</div>
                <p className="caption">
                  The plain-English note a race engineer would send to the pit
                  wall, synthesized from tone, pace, and agreement.
                </p>
              </div>
            </div>
          </div>

          <div className="grid-2" style={{ marginBottom: 16 }}>
            <div className="panel">
              <div className="panel-head">
                <h2>Lap times</h2>
              </div>
              <div className="panel-body">
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={lapData}>
                      <CartesianGrid stroke="#2a3122" strokeDasharray="3 3" />
                      <XAxis dataKey="lap" stroke="#5f6a52" fontSize={11} />
                      <YAxis
                        domain={["auto", "auto"]}
                        stroke="#5f6a52"
                        fontSize={11}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "#181c13",
                          border: "1px solid #2a3122",
                          fontSize: 12,
                          fontFamily: "IBM Plex Mono",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="time"
                        stroke="#c8f04b"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="caption">
                  Clean lap times from FastF1. Dips and spikes are pace changes,
                  not necessarily stress.
                </p>
              </div>
            </div>

            <div className="panel">
              <div className="panel-head">
                <h2>Stress vs baseline pace</h2>
              </div>
              <div className="panel-body">
                <div className="chart-wrap">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={correlationData}>
                      <CartesianGrid stroke="#2a3122" strokeDasharray="3 3" />
                      <XAxis dataKey="lap" stroke="#5f6a52" fontSize={11} />
                      <YAxis domain={["auto", "auto"]} stroke="#5f6a52" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          background: "#181c13",
                          border: "1px solid #2a3122",
                          fontSize: 12,
                          fontFamily: "IBM Plex Mono",
                        }}
                      />
                      <Line
                        type="monotone"
                        dataKey="baseline"
                        stroke="#8b949e"
                        strokeWidth={2}
                        dot={false}
                      />
                      <Line
                        type="monotone"
                        dataKey="stress"
                        stroke="#ff5c4d"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="caption">
                  Grey = laps without a stress label, red = laps flagged as
                  stressed/tired. Divergence between the two is the correlation
                  signal.
                </p>
              </div>
            </div>
          </div>

          {timelineData.length > 0 && (
            <div className="panel" style={{ marginBottom: 16 }}>
              <div className="panel-head">
                <h2>Radio mood timeline</h2>
                <span className="mono-note">
                  {result.correlation?.sample_size ?? 0} labelled laps
                </span>
              </div>
              <div className="panel-body">
                <div className="timeline">
                  {timelineData.map((p) => (
                    <span
                      key={p.lap}
                      className={`mood-pill ${MOOD_CLASS[p.mood] ?? "Neutral"}`}
                      title={`Lap ${p.lap}: ${p.mood} (${(p.confidence * 100).toFixed(0)}%)`}
                    >
                      L{p.lap} {p.mood}
                    </span>
                  ))}
                </div>
                <p className="caption">
                  One mood per lap, taken from the driver's radio that lap. Hover a
                  pill for the confidence. Green = calm, red = stressed, amber =
                  tired.
                </p>
              </div>
            </div>
          )}

          <div className="panel">
            <div className="panel-head">
              <h2>Method note</h2>
            </div>
            <div className="panel-body">
              <p className="mono-note">
                Pearson r={result.correlation?.correlation?.toFixed(2) ?? "—"} at
                lag {result.correlation?.best_lag ?? 0} · p ={" "}
                {result.correlation?.p_value?.toFixed(3) ?? "—"}
              </p>
              <p className="mono-note">{result.correlation?.reasoning}</p>
              <p className="caption">
                This is the rigorous part: a real correlation with a p-value and a
                lag search, not a canned "stress detected" label. A negative lag
                means mood changes before pace — the early-warning property.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
