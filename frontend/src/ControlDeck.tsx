import { memo } from "react";
import { MODE_HELP, MODE_KEYS, MODE_LABELS, MODES, type Mode } from "./constants";

interface Props {
  mode: Mode;
  text: string;
  driver: string;
  gp: string;
  year: number;
  audio: File | null;
  loading: boolean;
  onModeChange: (mode: Mode) => void;
  onTextChange: (text: string) => void;
  onDriverChange: (driver: string) => void;
  onGpChange: (gp: string) => void;
  onYearChange: (year: number) => void;
  onAudioChange: (audio: File | null) => void;
  onRun: () => void;
}

export const ControlDeck = memo(function ControlDeck({
  mode,
  text,
  driver,
  gp,
  year,
  audio,
  loading,
  onModeChange,
  onTextChange,
  onDriverChange,
  onGpChange,
  onYearChange,
  onAudioChange,
  onRun,
}: Props) {
  return (
    <div className="control-deck">
      <div className="mode-stack">
        {MODES.map((m) => (
          <button
            key={m}
            className={`mode-tab ${mode === m ? "active" : ""}`}
            onClick={() => onModeChange(m)}
          >
            {MODE_LABELS[m]}
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
              onChange={(e) => onTextChange(e.target.value)}
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
              onChange={(e) => onAudioChange(e.target.files?.[0] ?? null)}
            />
            {audio ? audio.name : "Drop radio audio or click to upload"}
          </label>
        )}

        <div className="field">
          <label>Driver</label>
          <input
            value={driver}
            onChange={(e) => onDriverChange(e.target.value)}
            placeholder="VER"
          />
        </div>
        <div className="field">
          <label>Grand Prix</label>
          <input value={gp} onChange={(e) => onGpChange(e.target.value)} placeholder="Melbourne" />
        </div>
        <div className="field">
          <label>Season</label>
          <input
            type="number"
            value={year}
            onChange={(e) => {
              // Ignore empty/partial/out-of-range input instead of sending 0 or NaN.
              const n = Number(e.target.value);
              if (Number.isInteger(n) && n >= 2018 && n <= 2100) onYearChange(n);
            }}
            min={2018}
            max={2100}
            step={1}
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
        onClick={onRun}
        disabled={mode === "live" || loading || (mode === "audio" && !audio)}
      >
        {mode === "live"
          ? "Streaming automatically"
          : loading
            ? "Analysing…"
            : "Run analysis →"}
      </button>
    </div>
  );
});
