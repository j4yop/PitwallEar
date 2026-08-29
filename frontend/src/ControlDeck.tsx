import { memo } from "react";
import { PopButton } from "@/components/ui/pop-button";
import { CornerButton } from "@/components/ui/corner-button";
import { MODE_HELP, MODE_LABELS, MODES, type Mode } from "./constants";

interface Props {
  mode: Mode;
  text: string;
  driver: string;
  gp: string;
  year: number;
  audio: File | null;
  loading: boolean;
  elapsed: number;
  onModeChange: (mode: Mode) => void;
  onTextChange: (text: string) => void;
  onDriverChange: (driver: string) => void;
  onGpChange: (gp: string) => void;
  onYearChange: (year: number) => void;
  onAudioChange: (audio: File | null) => void;
  onRun: () => void;
}

const MODE_ACCENT: Record<Mode, string> = {
  demo: "var(--color-accent)",
  text: "var(--color-accent)",
  audio: "var(--color-accent)",
  live: "var(--color-accent)",
};

const MODE_HOTKEY: Record<Mode, string> = {
  demo: "1",
  text: "2",
  audio: "3",
  live: "4",
};

export const ControlDeck = memo(function ControlDeck({
  mode,
  text,
  driver,
  gp,
  year,
  audio,
  loading,
  elapsed,
  onModeChange,
  onTextChange,
  onDriverChange,
  onGpChange,
  onYearChange,
  onAudioChange,
  onRun,
}: Props) {
  const runLabel =
    mode === "live"
      ? "Streaming automatically"
      : loading
        ? `Analysing… ${elapsed}s (cold runs take a minute)`
        : "Run analysis →";

  return (
    <div className="control-deck">
      <div className="mode-stack">
        {MODES.map((m) => {
          const isActive = mode === m;
          return (
            <button
              key={m}
              onClick={() => onModeChange(m)}
              data-cursor="link"
              aria-pressed={isActive}
              className={`group relative block w-full text-left ${
                isActive ? "ring-2 ring-[var(--paper-ink,#171b12)]" : ""
              }`}
              style={{ background: "transparent", border: "none", padding: 0 }}
            >
              <PopButton
                className="!w-full"
                style={{
                  background: isActive ? MODE_ACCENT[m] : "transparent",
                  color: isActive ? "#fff" : "#171b12",
                  border: isActive
                    ? "2px solid #171b12"
                    : "1px solid #aab29b",
                  opacity: isActive ? 1 : 0.85,
                }}
              >
                <span className="flex w-full items-center justify-between">
                  <span className="font-[var(--display)] text-lg font-bold tracking-[0.08em] uppercase">
                    {MODE_LABELS[m]}
                  </span>
                  <span
                    className="font-mono text-[10px] tracking-widest"
                    style={{ color: isActive ? "rgba(255,255,255,0.7)" : "#878e7c" }}
                  >
                    [{MODE_HOTKEY[m]}]
                  </span>
                </span>
              </PopButton>
            </button>
          );
        })}
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

      <div className="self-end">
        <CornerButton
          onClick={onRun}
          disabled={mode === "live" || loading || (mode === "audio" && !audio)}
          accentColor="#ffd60a"
          showIcon={false}
        >
          <span className="font-[var(--display)] text-lg font-bold tracking-[0.08em] uppercase">
            {runLabel}
          </span>
        </CornerButton>
      </div>
    </div>
  );
});
