import { useMemo } from "react";
import { GooeyTextReveal } from "@/components/ui/gooey-text-reveal";
import { LapTimesChart, StressPaceChart } from "./Charts";
import { MOOD_CLASS, type AnalysisResponse } from "./constants";

function heroLag(result: AnalysisResponse): string {
  const lead = result.correlation?.risk_lead_time_laps;
  if (lead != null) {
    return `Mood leads pace by ${lead} lap${lead === 1 ? "" : "s"}`;
  }
  const lag = result.correlation?.best_lag;
  if (lag == null || lag === 0) return "Mood and pace aligned";
  const abs = Math.abs(lag);
  return `Best lag: ${lag < 0 ? "-" : "+"}${abs} lap${abs === 1 ? "" : "s"}`;
}

export function ResultView({ result }: { result: AnalysisResponse }) {
  const lapData = useMemo(
    () =>
      (result.pace.laps ?? [])
        .filter((p) => p.lap_time_s != null)
        .map((p) => ({ lap: p.lap, time: p.lap_time_s as number })),
    [result.pace.laps]
  );

  const correlationData = useMemo(() => {
    const baseline = (result.correlation?.non_stress_laps ?? [])
      .filter((p) => p.lap_time_s != null)
      .map((p) => ({ lap: p.lap, baseline: p.lap_time_s as number, stress: null }));
    const stressed = (result.correlation?.stress_laps ?? [])
      .filter((p) => p.lap_time_s != null)
      .map((p) => ({ lap: p.lap, baseline: null, stress: p.lap_time_s as number }));
    return [...baseline, ...stressed].sort((a, b) => a.lap - b.lap);
  }, [result.correlation?.non_stress_laps, result.correlation?.stress_laps]);

  const timelineData = useMemo(
    () =>
      (result.correlation?.mood_timeline ?? [])
        .slice()
        .sort((a, b) => a.lap - b.lap),
    [result.correlation?.mood_timeline]
  );

  const heroValue =
    result.correlation?.correlation == null
      ? "—"
      : result.correlation.correlation.toFixed(2);

  const toneClass =
    result.emotion.mood === "Calm"
      ? "calm"
      : result.emotion.mood === "Tired"
        ? "tired"
        : "stress";

  return (
    <>
      <div className="hero">
        <div className={`hero-metric ${toneClass}`}>
          <span className="label">Driver tone</span>
          <span className="value">{result.emotion.mood}</span>
          <span className="unit">
            {result.emotion.calibrated_confidence != null
              ? `${(result.emotion.calibrated_confidence * 100).toFixed(0)}% calibrated`
              : `${(result.emotion.confidence * 100).toFixed(0)}% confidence`}
          </span>
          <span className="caption">
            The mood detected from the radio clip — tone of voice (audio) or word
            choice (text). Calibrated confidence is a softer, more honest estimate
            than raw model probability.
          </span>
        </div>

        <div className="hero-metric primary">
          <span className="label">Stress → pace correlation</span>
          <span className="value">{heroValue}</span>
          <span className="unit">{heroLag(result)}</span>
          <span className="caption">
            How strongly the per-lap mood predicts lap time. Values near ±1 are
            strong; the lag tells you whether mood changes before pace.
          </span>
        </div>
      </div>

      {result.agreement && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Cross-model agreement</GooeyTextReveal></h2>
            <span className={`agreement-badge ${result.agreement.agrees ? "agree" : "disagree"}`}>
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
              Compares <em>how</em> the driver says it (tone) with <em>what</em>{" "}
              they say (words). A calm voice describing a serious problem is a
              disagreement worth flagging.
            </p>
          </div>
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="panel">
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Transcript</GooeyTextReveal></h2>
          </div>
          <div className="panel-body">
            <p className="insight-quote">{result.transcription.text || "(empty)"}</p>
            <p className="caption">
              The speech-to-text output for the uploaded or pasted radio message.
            </p>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Co-driver call</GooeyTextReveal></h2>
          </div>
          <div className="panel-body">
            <p className="insight-quote">{result.insight.summary}</p>
            <div className="action-call">{result.insight.action}</div>
            <p className="caption">
              The plain-English note a race engineer would send to the pit wall,
              synthesized from tone, pace, and agreement.
            </p>
          </div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="panel">
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Lap times</GooeyTextReveal></h2>
          </div>
          <div className="panel-body">
            <LapTimesChart data={lapData} />
            <p className="caption">
              Clean lap times from FastF1. Dips and spikes are pace changes, not
              necessarily stress.
            </p>
          </div>
        </div>

        <div className="panel">
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Stress vs baseline pace</GooeyTextReveal></h2>
          </div>
          <div className="panel-body">
            <StressPaceChart data={correlationData} />
            <p className="caption">
              Grey = laps without a stress label, red = laps flagged as
              stressed/tired. Divergence between the two is the correlation signal.
            </p>
          </div>
        </div>
      </div>

      {timelineData.length > 0 && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Radio mood timeline</GooeyTextReveal></h2>
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
                  title={
                    p.calibrated_confidence != null
                      ? `Lap ${p.lap}: ${p.mood} (${(p.calibrated_confidence * 100).toFixed(0)}% calibrated)`
                      : `Lap ${p.lap}: ${p.mood} (${(p.confidence * 100).toFixed(0)}%)`
                  }
                >
                  L{p.lap} {p.mood}
                </span>
              ))}
            </div>
            <p className="caption">
              One mood per lap, taken from the driver's radio that lap. Hover a pill
              for the confidence. Green = calm, red = stressed, amber = tired.
            </p>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-head">
          <h2><GooeyTextReveal mode="immediate">Method note</GooeyTextReveal></h2>
        </div>
        <div className="panel-body">
          <p className="mono-note">
            Pearson r={result.correlation?.correlation?.toFixed(2) ?? "—"} at lag{" "}
            {result.correlation?.best_lag ?? 0} · p ={" "}
            {result.correlation?.p_value?.toFixed(3) ?? "—"}
          </p>
          <p className="mono-note">{result.correlation?.reasoning}</p>
          <p className="caption">
            This is the rigorous part: a real correlation with a p-value and a lag
            search, not a canned "stress detected" label. A negative lag means mood
            changes before pace — the early-warning property.
          </p>
        </div>
      </div>

      {result.correlation?.causal && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Causal lead-lag analysis</GooeyTextReveal></h2>
            <span className="mono-note">
              {result.correlation.causal.method.replace("_", " ")}
            </span>
          </div>
          <div className="panel-body">
            <p className="mono-note">
              {result.correlation.causal.direction} · p ={" "}
              {result.correlation.causal.p_value.toFixed(4)}
            </p>
            <p className="mono-note">{result.correlation.causal.reasoning}</p>
            <p className="caption">
              Tests whether mood <em>leads</em> pace rather than merely co-moving.
              Uses Granger causality for larger samples and transfer entropy for
              small ones. A significant negative lag is the early-warning signal.
            </p>
          </div>
        </div>
      )}

      {result.explainability && result.explainability.failure_modes.length > 0 && (
        <div className="panel" style={{ marginTop: 16 }}>
          <div className="panel-head">
            <h2><GooeyTextReveal mode="immediate">Honest failure modes</GooeyTextReveal></h2>
          </div>
          <div className="panel-body">
            {result.explainability.failure_modes.map((mode) => (
              <p key={mode} className="mono-note">
                · {mode}
              </p>
            ))}
            <p className="caption">
              These are the places this analysis could be wrong. We surface them
              deliberately so the co-driver is auditable, not a black box.
            </p>
          </div>
        </div>
      )}
    </>
  );
}
