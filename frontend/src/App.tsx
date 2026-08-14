import { useCallback, useState } from "react";
import { ControlDeck } from "./ControlDeck";
import { LiveView } from "./LiveView";
import { ResultView } from "./ResultView";
import type { AnalysisResponse, Mode } from "./constants";

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

  const run = useCallback(async () => {
    if (mode === "live") {
      // Live mode is self-streaming; no discrete run action needed.
      setResult(null);
      return;
    }
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
  }, [mode, text, driver, gp, year, audio]);

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

      <ControlDeck
        mode={mode}
        text={text}
        driver={driver}
        gp={gp}
        year={year}
        audio={audio}
        loading={loading}
        onModeChange={setMode}
        onTextChange={setText}
        onDriverChange={setDriver}
        onGpChange={setGp}
        onYearChange={setYear}
        onAudioChange={setAudio}
        onRun={run}
      />

      {error && (
        <div className="panel" style={{ marginBottom: 16, padding: 12 }}>
          <span style={{ color: "var(--red)" }}>{error}</span>
        </div>
      )}

      {mode === "live" && (
        <LiveView driver={driver} gp={gp} year={year} />
      )}

      {mode !== "live" && !result && !loading && (
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
                PitwallEar reads a radio message, labels the driver's tone, aligns it
                to a per-lap mood timeline, and correlates that timeline with pace.
                The headline metric is the stress-pace correlation and its lag — mood
                leading pace is the early-warning signal a race engineer actually
                needs.
              </p>
            </div>
          </div>
        </div>
      )}

      {mode !== "live" && result && <ResultView result={result} />}
    </div>
  );
}
