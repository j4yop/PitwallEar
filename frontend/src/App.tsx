import { useCallback, useEffect, useRef, useState } from "react";
import { ControlDeck } from "./ControlDeck";
import { LiveView } from "./LiveView";
import { ResultView } from "./ResultView";
import type { AnalysisResponse, Mode } from "./constants";

// Analyses can take minutes on a cold backend; give up before the user does.
const ANALYSIS_TIMEOUT_MS = 120_000;

async function fetchOrThrow(url: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(url, init);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res;
}

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

  const abortRef = useRef<AbortController | null>(null);
  const runIdRef = useRef(0);
  const cancelReasonRef = useRef<"timeout" | "mode-change" | null>(null);

  // Cancel any in-flight analysis when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const handleModeChange = useCallback(
    (next: Mode) => {
      if (next === mode) return;
      // A late response must never land under the new tab.
      cancelReasonRef.current = "mode-change";
      abortRef.current?.abort();
      setResult(null);
      setError("");
      setMode(next);
    },
    [mode]
  );

  const run = useCallback(async () => {
    if (mode === "live") {
      // Live mode is self-streaming; no discrete run action needed.
      setResult(null);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = ++runIdRef.current;
    const superseded = () => runIdRef.current !== requestId;
    const signal = controller.signal;

    setLoading(true);
    setError("");
    setResult(null);

    const timeout = setTimeout(() => {
      cancelReasonRef.current = "timeout";
      controller.abort();
    }, ANALYSIS_TIMEOUT_MS);

    try {
      if (mode === "demo") {
        const res = await fetchOrThrow("/demo", { signal });
        if (superseded()) return;
        setResult(await res.json());
        return;
      }

      if (mode === "text") {
        const res = await fetchOrThrow("/analyse-text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, driver, gp, year }),
          signal,
        });
        if (superseded()) return;
        setResult(await res.json());
        return;
      }

      if (!audio) return;
      const form = new FormData();
      form.append("audio", audio);
      form.append("driver", driver);
      form.append("gp", gp);
      form.append("year", String(year));
      const res = await fetchOrThrow("/analyse", { method: "POST", body: form, signal });
      if (superseded()) return;
      setResult(await res.json());
    } catch (e) {
      if (signal.aborted) {
        if (cancelReasonRef.current === "timeout" && !superseded()) {
          setError(`Analysis timed out after ${ANALYSIS_TIMEOUT_MS / 1000}s.`);
        }
        // Mode-switch aborts stay silent — the UI has already moved on.
        return;
      }
      if (!superseded()) {
        setError(e instanceof Error ? e.message : "Unknown error");
      }
    } finally {
      clearTimeout(timeout);
      if (!superseded()) {
        setLoading(false);
      }
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
        onModeChange={handleModeChange}
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
