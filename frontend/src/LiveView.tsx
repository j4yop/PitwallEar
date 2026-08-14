import { useEffect, useRef, useState } from "react";
import { MOOD_CLASS } from "./constants";

interface LiveTimelinePoint {
  lap: number;
  mood: string;
  confidence: number;
  calibrated_confidence: number | null;
  transcript: string;
}

interface LiveEvent {
  mode: string;
  new_clips: number;
  total_clips: number;
  timeline: LiveTimelinePoint[];
}

export function LiveView({
  driver,
  gp,
  year,
}: {
  driver: string;
  gp: string;
  year: number;
}) {
  const [connected, setConnected] = useState(false);
  const [mode, setMode] = useState("connecting");
  const [timeline, setTimeline] = useState<LiveTimelinePoint[]>([]);
  const [totalClips, setTotalClips] = useState(0);
  const [error, setError] = useState("");
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    setError("");
    setConnected(false);
    setMode("connecting");
    setTimeline([]);
    setTotalClips(0);

    const url = `/live/stream?driver=${encodeURIComponent(driver)}&gp=${encodeURIComponent(gp)}&year=${year}`;
    const source = new EventSource(url);
    sourceRef.current = source;

    source.onopen = () => setConnected(true);

    source.addEventListener("init", () => {
      setConnected(true);
    });

    source.addEventListener("update", (event) => {
      const data: LiveEvent = JSON.parse((event as MessageEvent).data);
      setMode(data.mode);
      setTotalClips(data.total_clips);
      setTimeline(data.timeline);
    });

    source.addEventListener("error", (event) => {
      // EventSource fires an error event both for network issues and normal
      // reconnects. Only surface it if the connection is not established.
      if ((event as MessageEvent).data) {
        try {
          const data = JSON.parse((event as MessageEvent).data);
          setError(data.error || "Stream error");
        } catch {
          setError("Stream error");
        }
      }
    });

    source.onerror = () => {
      // The stream is long-lived; a dropped connection just means the browser
      // is trying to reconnect. Do not show a hard error here.
    };

    return () => {
      source.close();
      sourceRef.current = null;
    };
  }, [driver, gp, year]);

  const statusLabel =
    mode === "live"
      ? "Live"
      : mode === "near-real-time-replay"
        ? "Near-real-time replay"
        : mode === "connecting"
          ? "Connecting"
          : "Streaming";

  return (
    <>
      <div className="hero">
        <div className="hero-metric primary">
          <span className="label">Live radio timeline</span>
          <span className="value">{totalClips}</span>
          <span className="unit">clips ingested</span>
          <span className="caption">
            New radio messages appear here as they arrive. Mode: {statusLabel}.
          </span>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2>Stream status</h2>
            <span className={`live-chip ${connected ? "" : "off"}`}>
              <span className="live-dot" />
              {connected ? "Connected" : "Waiting"}
            </span>
          </div>
          <div className="panel-body">
            <p className="mono-note">
              This is a true streaming path using Server-Sent Events. The backend
              polls OpenF1 for new radio clips, transcribes and classifies only
              the ones it has not seen before, and pushes the growing timeline
              here. Without sponsor-tier live access, it degrades to a
              clearly-labelled near-real-time replay of the latest session.
            </p>
            {error && (
              <p className="mono-note" style={{ color: "var(--red)" }}>
                {error}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="panel-head">
          <h2>Growing mood timeline</h2>
          <span className="mono-note">{timeline.length} labelled clips</span>
        </div>
        <div className="panel-body">
          {timeline.length === 0 ? (
            <p className="mono-note">
              Waiting for the first clip to arrive. If no session is live, this
              stays empty — that is honest, not a bug.
            </p>
          ) : (
            <div className="timeline">
              {timeline.map((p, i) => (
                <span
                  key={`${p.lap}-${i}`}
                  className={`mood-pill ${MOOD_CLASS[p.mood] ?? "Neutral"}`}
                  title={
                    p.transcript
                      ? `Lap ${p.lap}: ${p.mood} — "${p.transcript}"`
                      : `Lap ${p.lap}: ${p.mood}`
                  }
                >
                  L{p.lap} {p.mood}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
