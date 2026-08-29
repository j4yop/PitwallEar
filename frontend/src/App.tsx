import { useCallback, useEffect, useRef, useState } from "react";
import { GooeyTextReveal } from "@/components/ui/gooey-text-reveal";
import { StructureFlowCollection } from "@/shaders";
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
    throw new Error(
      "Can't reach the app server. Restart both servers with ./dev.sh from the repo root and reload this page."
    );
  }
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    if (res.status >= 500 && !body.trim().startsWith("{")) {
      throw new Error(
        "Backend API is not responding (the dashboard loaded, but the API on :8000 didn't answer). Start it with ./dev.sh, then run again."
      );
    }
    throw new Error(body || `Request failed: ${res.status}`);
  }
  return res;
}

function readError(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
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

  useEffect(() => {
    document.body.classList.add("dashboard");
    return () => document.body.classList.remove("dashboard");
  }, []);

  // Heartbeat the API so the "live" chip reflects reality.
  const [apiOnline, setApiOnline] = useState<boolean | null>(null);
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const res = await fetch("/health", { cache: "no-store" });
        if (alive) setApiOnline(res.ok);
      } catch {
        if (alive) setApiOnline(false);
      }
    };
    check();
    const t = setInterval(check, 10_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  // Live mode: open a Server-Sent Events stream and append the latest lap
  // timeline to the result on every event. Stays open while the tab is
  // focused, no polling.
  useEffect(() => {
    if (mode !== "live") return;
    const es = new EventSource("/live");
    es.onmessage = (e) => {
      try {
        const payload = JSON.parse(e.data) as AnalysisResponse;
        setResult(payload);
      } catch {
        // ignore malformed lines
      }
    };
    es.onerror = () => {
      // Auto-reconnect is built in; just keep the latest good state.
    };
    return () => es.close();
  }, [mode]);

  // Wall-clock elapsed counter while a run is in flight.
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!loading) return;
    setElapsed(0);
    const start = Date.now();
    const t = setInterval(() => setElapsed(Math.round((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(t);
  }, [loading]);

  const runAnalysis = useCallback(async () => {
    if (mode === "live") return;
    if (mode === "audio" && !audio) return;
    setLoading(true);
    setResult(null);
    try {
      const ctrl = new AbortController();
      const t = setTimeout(() => ctrl.abort(), ANALYSIS_TIMEOUT_MS);
      let res: Response;
      if (mode === "demo") {
        res = await fetchOrThrow("/demo", { signal: ctrl.signal });
      } else if (mode === "text") {
        res = await fetchOrThrow("/analyse-text", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify({ text, driver, gp, year }),
          signal: ctrl.signal,
        });
      } else {
        const fd = new FormData();
        fd.append("audio", audio!);
        fd.append("driver", driver);
        fd.append("gp", gp);
        fd.append("year", String(year));
        res = await fetchOrThrow("/analyse", { method: "POST", body: fd, signal: ctrl.signal });
      }
      const data = (await res.json()) as AnalysisResponse;
      setResult(data);
      clearTimeout(t);
    } catch (err) {
      setResult({
        error: readError(err),
      } as unknown as AnalysisResponse);
    } finally {
      setLoading(false);
    }
  }, [mode, text, audio, driver, gp, year]);

  return (
    <>
      <div
        aria-hidden
        style={{
          position: "fixed",
          inset: 0,
          zIndex: 0,
          pointerEvents: "none",
        }}
      >
        <StructureFlowCollection
          variant="flux-vortex"
          speed={0.6}
          density={1}
        />
      </div>
      <div className="app" style={{ position: "relative", zIndex: 1 }}>
        <header className="topbar">
          <div className="brand">
            <div className="brand-mark">
              <GooeyTextReveal mode="immediate">PITWALL<span>EAR</span></GooeyTextReveal>
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
              ? "API offline"
              : apiOnline === null
                ? "Connecting…"
                : "API online"}
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
          onModeChange={setMode}
          onTextChange={setText}
          onDriverChange={setDriver}
          onGpChange={setGp}
          onYearChange={setYear}
          onAudioChange={setAudio}
          onRun={runAnalysis}
        />

        {mode === "live" && <LiveView driver={driver} gp={gp} year={year} />}

        {!result && !loading && mode !== "live" && (
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
                <h2><GooeyTextReveal mode="immediate">What this does</GooeyTextReveal></h2>
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
    </>
  );
}
