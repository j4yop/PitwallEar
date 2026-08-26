import { useCallback, useEffect, useRef, useState } from "react";
import { ControlDeck } from "./ControlDeck";
import { LiveView } from "./LiveView";
import { ResultView } from "./ResultView";
import type { AnalysisResponse, Mode } from "./constants";

// Analyses can take minutes on a cold backend; give up before the user does.
const ANALYSIS_TIMEOUT_MS = 120_000;

async function fetchOrThrow(url: string, init?: RequestInit): Promise<Response> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    // Network-level failure: the dev server itself is unreachable (stale tab).
    throw new Error(
      "Can't reach the app server. Restart both servers with ./dev.sh from the repo root and reload this page."
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    // A 5xx whose body isn't JSON is the Vite proxy failing to reach the
    // backend, not the API answering — tell the user how to fix it.
    if (res.status >= 500 && !body.trim().startsWith("{")) {
      throw new Error(
        "Backend API is not responding (the dashboard loaded, but the API on :8000 didn't answer). Start it with ./dev.sh, then run again."
      );
    }
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
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  const [elapsed, setElapsed] = useState(0);

  // Heartbeat the API so "Run analysis" never fails silently: the header chip
  // shows at a glance whether the backend is up.
  useEffect(() => {
    let alive = true;
    const ping = () =>
      fetch("/health")
        .then((r) => alive && setApiOnline(r.ok))
        .catch(() => alive && setApiOnline(false));
    ping();
    const t = setInterval(ping, 10_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  // Elapsed counter so a slow (normal!) analysis doesn't read as "nothing is
  // happening". Cold FastF1 downloads routinely take 30-60s.
  useEffect(() => {
    if (!loading) return;
    const t = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [loading]);

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
    setElapsed(0);

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
        <div className="live-chip" title={apiOnline === false ? "The API on :8000 is not responding — start it with ./dev.sh" : undefined}>
          <span
            className="live-dot"
            style={
              apiOnline === false
                ? { background: "var(--red)", boxShadow: "0 0 8px var(--red)" }
                : undefined
            }
          />
          {apiOnline === false
            ? "API offline — run ./dev.sh"
            : result
              ? "Analysis complete"
              : loading
                ? `Analysing… ${elapsed}s`
                : "Ready"}
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
        elapsed={elapsed}
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
