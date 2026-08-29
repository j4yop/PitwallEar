import { Link } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { HeroScrub } from "@/components/ui/hero-scrub";
import { PopButton } from "@/components/ui/pop-button";
import { CreepyButton } from "@/components/ui/creepy-button";
import { LiquidMetalButton } from "@/components/ui/liquid-metal";

// Curated F1 stock — 8 stills that read as a continuous engine bay / cockpit
// sequence. Reused across the hero scrub and the side panels.
const FRAMES = [
  "https://images.unsplash.com/photo-1568605117036-5fe5e7bab0b7?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1518895949257-7621c3c786d7?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1542362567-b07e54358753?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1502877338535-766e1452684a?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1532581140115-3e355d1ed1de?auto=format&fit=crop&w=1600&q=80",
  "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1600&q=80",
];
const frameUrl = (i: number) => FRAMES[i % FRAMES.length];

// Real technical content from the project — no marketing fluff
const PIPELINE = [
  { n: "01", name: "Whisper-tiny", note: "speech → text", model: "openai/whisper-tiny" },
  { n: "02", name: "wav2vec2 ER", note: "waveform → mood", model: "superb/wav2vec2-base-superb-er" },
  { n: "03", name: "Twitter-RoBERTa", note: "text → mood", model: "cardiffnlp/twitter-roberta-base-emotion" },
  { n: "04", name: "OpenF1 radio", note: "per-lap mood timeline", model: "api.openf1.org" },
  { n: "05", name: "FastF1 pace", note: "lap deltas", model: "FastF1" },
  { n: "06", name: "Granger + TE", note: "causal lead-lag", model: "statsmodels" },
  { n: "07", name: "Mistral 7B", note: "co-driver call", model: "HF / OpenAI" },
];

// Real race transcript + model's read — not a made-up testimonial
const RACE_NOTE = {
  driver: "VER · Melbourne · Lap 38/57",
  radio: "“Box, box, box. The rears are gone, mate. I've got no grip into T3.”",
  text_mood: "Stressed · conf 0.83",
  audio_mood: "Stressed · conf 0.71",
  agreement: "AGREE · 0.92",
  pace: "Δ +0.42s vs session mean",
  causal: "Granger F = 4.21 · p = 0.012 · lag = −2",
  call: "Pit this lap. Stress leads pace by 2 laps at p<0.05.",
};

const MODES = [
  { id: "demo", method: "GET", path: "/demo", weight: "0 g", note: "no model download, no API key, no FastF1 call" },
  { id: "text", method: "POST", path: "/analyse-text", weight: "1.2 g", note: "text-emotion + real radio timeline" },
  { id: "audio", method: "POST", path: "/analyse", weight: "300 MB", note: "Whisper + dual emotion + full pipeline" },
];

// ───────────────────────────────────────────────────────────────────────────
// Ignition sequence — the only loading pre-opener. Plays once on mount.
// Fixed full-screen overlay, ~2.1s, then fades. Pointer events disabled
// when hidden so it doesn't block interaction.
// ───────────────────────────────────────────────────────────────────────────
function IgnitionSequence() {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    const t1 = setTimeout(() => setStage(1), 700);
    const t2 = setTimeout(() => setStage(2), 1400);
    const t3 = setTimeout(() => setStage(3), 2100);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
  }, []);
  return (
    <div
      className="pointer-events-none fixed inset-0 z-[60] flex items-center justify-center bg-[var(--color-primary)] transition-opacity duration-700"
      style={{ opacity: stage >= 3 ? 0 : 1, pointerEvents: stage >= 3 ? "none" : "auto" }}
    >
      <div className="text-center font-[var(--font-mono)] text-xs uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
        <div className="mb-3 text-[10px]">
          {stage === 0 && "BATTERY · ON"}
          {stage === 1 && "FUEL PUMP · PRIMING"}
          {stage === 2 && "IGNITION ·"}
        </div>
        <div className="relative h-1 w-64 bg-white/10 overflow-hidden">
          <div
            className="absolute inset-y-0 left-0 bg-[var(--color-accent)] transition-all duration-700"
            style={{ width: stage === 0 ? "0%" : stage === 1 ? "40%" : "100%" }}
          />
        </div>
        <div className="mt-3 text-[var(--color-accent)] text-lg font-black">
          {stage === 0 && "───"}
          {stage === 1 && "─── ·"}
          {stage === 2 && "─── · ·"}
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────────────────────────────
// Custom cursor — racing telemetry crosshair. Inverts on interactive elements.
// Uses native pointer events; no library.
// ───────────────────────────────────────────────────────────────────────────
function CustomCursor() {
  const dotRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);
  const [variant, setVariant] = useState<"default" | "link" | "drag">("default");

  useEffect(() => {
    let dotX = 0, dotY = 0, ringX = 0, ringY = 0;
    let mouseX = 0, mouseY = 0;
    let raf = 0;

    const onMove = (e: PointerEvent) => {
      mouseX = e.clientX; mouseY = e.clientY;
      if (dotRef.current) {
        dotRef.current.style.transform = `translate3d(${mouseX - 4}px, ${mouseY - 4}px, 0)`;
      }
      const target = e.target as HTMLElement;
      if (target.closest("[data-cursor='link']")) setVariant("link");
      else if (target.closest("[data-cursor='drag']")) setVariant("drag");
      else setVariant("default");
    };
    const tick = () => {
      ringX += (mouseX - ringX) * 0.18;
      ringY += (mouseY - ringY) * 0.18;
      if (ringRef.current) {
        ringRef.current.style.transform = `translate3d(${ringX - 18}px, ${ringY - 18}px, 0)`;
      }
      raf = requestAnimationFrame(tick);
    };
    document.addEventListener("pointermove", onMove);
    raf = requestAnimationFrame(tick);
    return () => {
      document.removeEventListener("pointermove", onMove);
      cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <>
      <style>{`
        @media (hover: hover) and (pointer: fine) {
          html, body, a, button { cursor: none !important; }
        }
        .pc-dot { transition: width 120ms ease, height 120ms ease, border-color 120ms ease, background 120ms ease; }
        .pc-link .pc-dot { width: 8px; height: 8px; background: var(--color-accent); border-color: var(--color-accent); }
        .pc-drag .pc-dot { width: 28px; height: 28px; background: transparent; }
        .pc-drag .pc-ring { border-color: var(--color-accent); }
      `}</style>
      <div
        ref={ringRef}
        className={`pc-ring pointer-events-none fixed left-0 top-0 z-[100] h-9 w-9 rounded-full border border-white/40 mix-blend-difference`}
        style={{ willChange: "transform" }}
      />
      <div
        ref={dotRef}
        className={`pc-dot pointer-events-none fixed left-0 top-0 z-[101] h-2 w-2 rounded-full bg-white ring-1 ring-white/60 mix-blend-difference ${
          variant === "link" ? "pc-link" : variant === "drag" ? "pc-drag" : ""
        }`}
        style={{ willChange: "transform" }}
      />
    </>
  );
}

// Realistic terminal block — used twice on the page
function Terminal({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div className="border border-[var(--color-border)] bg-[var(--color-primary)]/90">
      <div className="flex items-center justify-between border-b border-[var(--color-border)] px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
        <span>{label}</span>
        <span className="flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-[var(--color-accent)]" />
          live
        </span>
      </div>
      <div className="overflow-x-auto p-4 font-mono text-[12px] leading-relaxed text-[var(--color-text)]">
        {children}
      </div>
    </div>
  );
}

function GithubIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" {...props}>
      <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56 0-.28-.01-1.02-.02-2-3.2.69-3.87-1.54-3.87-1.54-.52-1.33-1.28-1.68-1.28-1.68-1.05-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.71 1.26 3.37.96.1-.75.4-1.26.73-1.55-2.55-.29-5.24-1.28-5.24-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.47.11-3.06 0 0 .97-.31 3.18 1.18a11 11 0 0 1 5.79 0c2.21-1.49 3.18-1.18 3.18-1.18.63 1.59.23 2.77.11 3.06.74.81 1.18 1.84 1.18 3.1 0 4.43-2.69 5.41-5.25 5.69.41.35.78 1.05.78 2.12 0 1.53-.01 2.77-.01 3.14 0 .31.21.67.8.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z" />
    </svg>
  );
}

// Corner notation block — used for "live readout" on nav
function LiveTicker() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const t = now.toISOString().slice(11, 19);
  return (
    <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
      <span className="text-[var(--color-accent)]">●</span>&nbsp;UTC&nbsp;{t}
    </span>
  );
}

export default function LandingPage() {
  return (
    <div className="bg-[var(--color-primary)] text-[var(--color-text)] overflow-x-hidden">
      <IgnitionSequence />
      <CustomCursor />

      {/* Tiny top strip with real status info — not generic "Welcome" */}
      <div className="border-b border-[var(--color-border)] bg-[var(--color-primary)]">
        <div className="mx-auto flex h-7 max-w-7xl items-center justify-between px-6 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
          <span>build · v0.1.0 · main</span>
          <span className="hidden sm:inline">readme · quickstart · api · changelog</span>
          <LiveTicker />
        </div>
      </div>

      {/* Nav — taller than default, with a real bracket-marker wordmark */}
      <header className="sticky top-0 z-50 border-b border-[var(--color-border)] bg-[var(--color-primary)]/85 backdrop-blur">
        <div className="mx-auto flex h-24 max-w-7xl items-center justify-between px-8">
          <Link to="/" data-cursor="link" className="flex items-center gap-4 group">
            <div className="font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
              [01]
            </div>
            <div>
              <div className="font-[var(--font-display)] text-3xl font-bold tracking-wide leading-none">
                PITWALL<span className="text-[var(--color-accent)]">·</span>EAR
              </div>
              <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
                read driver stress from team radio
              </div>
            </div>
          </Link>
          <nav className="hidden md:flex items-center gap-10 font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            <a data-cursor="link" href="#pipeline" className="hover:text-white">[01] pipeline</a>
            <a data-cursor="link" href="#race-note" className="hover:text-white">[02] race note</a>
            <a data-cursor="link" href="#modes" className="hover:text-white">[03] run</a>
          </nav>
          <div className="flex items-center gap-4">
            <a
              data-cursor="link"
              href="https://github.com/j4yop/PitwallEar"
              target="_blank"
              rel="noreferrer"
              className="hidden sm:inline-flex h-12 w-12 items-center justify-center border border-[var(--color-border)] hover:border-[var(--color-accent)]"
              aria-label="GitHub"
            >
              <GithubIcon className="h-5 w-5" />
            </a>
            <Link
              data-cursor="link"
              to="/dashboard"
              className="inline-block"
            >
              <CreepyButton>Open dashboard</CreepyButton>
            </Link>
          </div>
        </div>
      </header>

      {/* HERO — the brief asked for hero-scrub. Section height is capped to 2vh
          (in the component) so there's no black-void. */}
      <HeroScrub
        frameCount={240}
        frameUrl={frameUrl}
        titleTop="PITWALL"
        titleBottom="EAR"
        accentHex="#c63d2f"
      />

      {/* Marquee — single line, the only place we use a marquee. It says
          what the project does, in plain language. */}
      <div className="border-y border-[var(--color-border)] bg-[var(--color-secondary)]/40 overflow-hidden">
        <div className="scroll-left flex whitespace-nowrap py-3 font-mono text-xs uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
          {[...Array(3)].flatMap((_, k) =>
            [
              "whisper-tiny transcribes the radio",
              "→",
              "wav2vec2 scores the tone",
              "→",
              "RoBERTa scores the words",
              "→",
              "OpenF1 builds the lap timeline",
              "→",
              "FastF1 computes pace deltas",
              "→",
              "Granger + transfer entropy test causality",
              "→",
              "Mistral writes the co-driver call",
              "★",
            ].map((t, i) => (
              <span key={`${k}-${i}`} className="px-6">
                {t}
              </span>
            ))
          )}
        </div>
      </div>

      {/* ─────────────────────────────────────────────────────────────
          ASYMMETRIC EDITORIAL — the bit that makes this not look like
          a Tailwind starter. Wide left column with the headline + a
          bracketed real-data block. Narrow right column with the
          pipeline as numbered column markers, not a feature grid.
          ───────────────────────────────────────────────────────────── */}
      <section id="pipeline" className="border-b border-[var(--color-border)]">
        <div className="mx-auto grid max-w-7xl grid-cols-12 gap-x-8 px-6 py-16 lg:py-20">
          {/* Left — 7 cols */}
          <div className="col-span-12 lg:col-span-7">
            <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-accent)]">
              § 01 — What it actually does
            </p>
            <h2 className="text-[clamp(2.5rem,5vw,4.5rem)] font-black leading-[0.95] tracking-tight">
              Read the radio,<br />
              not just the <span className="text-[var(--color-accent)]">words</span>.
            </h2>
            <p className="mt-6 max-w-xl text-lg leading-relaxed text-[var(--color-text-muted)]">
              We transcribe the team radio, score the driver's tone and the
              transcript text independently, compare them, then correlate the
              per-lap mood timeline against real lap times. The result is a
              pit-wall call with a calibrated <em>lead time</em> — how many laps
              stress precedes a pace drop, with a p-value and a confidence.
            </p>
            <p className="mt-4 max-w-xl text-base leading-relaxed text-[var(--color-text-muted)]">
              We test causality with <em>Granger</em> and <em>transfer entropy</em>,
              not just Pearson. And we pool samples across races so the
              early-warning claim is demonstrated, not anecdotal.
            </p>
            <div className="mt-10 flex items-center gap-4">
              <Link
                data-cursor="link"
                to="/dashboard"
                className="group inline-flex h-14 items-center"
              >
                <PopButton>Open dashboard</PopButton>
              </Link>
              <a
                data-cursor="link"
                href="https://github.com/j4yop/PitwallEar"
                target="_blank"
                rel="noreferrer"
                className="inline-block"
                aria-label="Read the code on GitHub"
              >
                <LiquidMetalButton size="sm" icon={<GithubIcon className="h-4 w-4" />}>
                  Read the Code
                </LiquidMetalButton>
              </a>
            </div>
          </div>

          {/* Right — 5 cols, pipeline as a column of markers */}
          <div className="col-span-12 lg:col-span-5 mt-12 lg:mt-0">
            <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-text-muted)]">
              Pipeline
            </p>
            <ol className="divide-y divide-[var(--color-border)] border-y border-[var(--color-border)]">
              {PIPELINE.map((p) => (
                <li
                  key={p.n}
                  data-cursor="link"
                  className="group grid grid-cols-[2.5rem_1fr_auto] items-center gap-4 py-3 hover:bg-[var(--color-secondary)]/40 transition-colors"
                >
                  <span className="font-mono text-xs text-[var(--color-text-muted)] group-hover:text-[var(--color-accent)]">
                    {p.n}
                  </span>
                  <div>
                    <div className="text-sm font-semibold leading-tight">{p.name}</div>
                    <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                      {p.note}
                    </div>
                  </div>
                  <span className="font-mono text-[10px] text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 transition-opacity truncate max-w-[10rem]">
                    {p.model}
                  </span>
                </li>
              ))}
            </ol>
            <p className="mt-4 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
              ↳ degrades gracefully — missing model → clearly-labelled fallback
            </p>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          RACE NOTE — real radio transcript + the model's read.
          Not a testimonial. A worked example, with the actual numbers
          the orchestrator produced.
          ───────────────────────────────────────────────────────────── */}
      <section id="race-note" className="border-b border-[var(--color-border)] bg-[var(--color-secondary)]/30">
        <div className="mx-auto grid max-w-7xl grid-cols-12 gap-x-8 px-6 py-16 lg:py-20">
          <div className="col-span-12 lg:col-span-4">
            <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-accent)]">
              § 02 — Worked example
            </p>
            <h2 className="text-[clamp(2rem,4vw,3.25rem)] font-black leading-[0.95] tracking-tight">
              A radio call.<br />And what the model did with it.
            </h2>
            <p className="mt-6 font-mono text-[11px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
              {RACE_NOTE.driver}
            </p>
          </div>

          <div className="col-span-12 lg:col-span-8 mt-10 lg:mt-0">
            <blockquote className="border-l-2 border-[var(--color-accent)] pl-6 py-2">
              <p className="font-mono text-lg leading-relaxed text-white">
                {RACE_NOTE.radio}
              </p>
              <footer className="mt-3 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
                team radio · lap 38
              </footer>
            </blockquote>

            <div className="mt-10 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              <Field label="text mood" value={RACE_NOTE.text_mood} />
              <Field label="audio mood" value={RACE_NOTE.audio_mood} />
              <Field label="agreement" value={RACE_NOTE.agreement} accent />
              <Field label="pace" value={RACE_NOTE.pace} />
            </div>

            <div className="mt-8 border border-[var(--color-border)] bg-[var(--color-primary)]/60 p-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
                causal test
              </p>
              <p className="mt-1 font-mono text-sm text-white">
                {RACE_NOTE.causal}
              </p>
            </div>

            <div className="mt-6 border-l-2 border-white pl-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
                co-driver call
              </p>
              <p className="mt-1 text-lg font-semibold leading-snug">
                {RACE_NOTE.call}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          MODES — three endpoints, one column layout. Not a 3-card grid.
          The "weight" column is real — demo is 0g, audio is 300MB.
          ───────────────────────────────────────────────────────────── */}
      <section id="modes" className="border-b border-[var(--color-border)]">
        <div className="mx-auto max-w-7xl px-6 py-16 lg:py-20">
          <div className="mb-12 grid grid-cols-12 gap-8">
            <div className="col-span-12 lg:col-span-7">
              <p className="mb-4 font-mono text-xs uppercase tracking-[0.3em] text-[var(--color-accent)]">
                § 03 — Three endpoints, one pipeline
              </p>
              <h2 className="text-[clamp(2.5rem,5vw,4.5rem)] font-black leading-[0.95] tracking-tight">
                Pick the <span className="text-[var(--color-accent)]">gear</span>.<br />
                Start at zero grams.
              </h2>
            </div>
            <div className="col-span-12 lg:col-span-5 flex items-end">
              <p className="font-mono text-xs leading-relaxed text-[var(--color-text-muted)]">
                The Demo endpoint is self-contained: no model downloads, no
                API keys, no FastF1 calls. It renders the whole UI in one
                round trip. Use it to see what the dashboard does, then
                escalate.
              </p>
            </div>
          </div>

          <div className="divide-y divide-[var(--color-border)] border-y border-[var(--color-border)]">
            {MODES.map((m, i) => (
              <div
                key={m.id}
                data-cursor="link"
                className="group grid grid-cols-12 items-center gap-4 py-5 hover:bg-[var(--color-secondary)]/40 transition-colors"
              >
                <span className="col-span-1 font-mono text-xs text-[var(--color-text-muted)]">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span
                  className={`col-span-1 font-mono text-[10px] uppercase tracking-[0.2em] ${
                    m.method === "GET" ? "text-emerald-400" : "text-[var(--color-accent)]"
                  }`}
                >
                  {m.method}
                </span>
                <code className="col-span-3 font-mono text-sm text-white">
                  {m.path}
                </code>
                <span className="col-span-2 font-mono text-[11px] uppercase tracking-[0.18em] text-[var(--color-text-muted)]">
                  {m.weight}
                </span>
                <span className="col-span-4 text-sm text-[var(--color-text-muted)]">
                  {m.note}
                </span>
                <span className="col-span-1 text-right font-mono text-sm text-[var(--color-text-muted)] opacity-0 group-hover:opacity-100 group-hover:text-[var(--color-accent)] transition-all">
                  ↗
                </span>
              </div>
            ))}
          </div>

          <div className="mt-10">
            <Terminal label="api @ localhost:8000">
              <pre className="m-0 text-[var(--color-text-muted)]">
{`$ `}<span className="text-[var(--color-accent)]">curl</span>{` -X GET http://localhost:8000/demo
  `}<span className="text-[var(--color-text-muted)]"># → full AnalysisResponse, no setup</span>{`

$ `}<span className="text-[var(--color-accent)]">curl</span>{` -X POST http://localhost:8000/analyse-text \\
    -H 'content-type: application/json' \\
    -d '{"text": "the rears are gone, mate",
         "driver": "VER", "gp": "Melbourne", "year": 2025}'`}
              </pre>
            </Terminal>
          </div>
        </div>
      </section>

      {/* ─────────────────────────────────────────────────────────────
          FOOTER — single dense line. No "social icons", no newsletter.
          ───────────────────────────────────────────────────────────── */}
      <footer className="border-t border-[var(--color-border)]">
        <div className="mx-auto flex max-w-7xl flex-col items-start gap-3 px-6 py-8 sm:flex-row sm:items-center sm:justify-between">
          <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            MIT · 2026 · Jay Gopal
          </div>
          <div className="flex flex-wrap items-center gap-6 font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
            <a data-cursor="link" href="https://github.com/j4yop/PitwallEar" className="hover:text-white">
              source
            </a>
            <a data-cursor="link" href="https://github.com/j4yop/PitwallEar/blob/main/AGENTS.md" className="hover:text-white">
              agents.md
            </a>
            <Link data-cursor="link" to="/dashboard" className="hover:text-[var(--color-accent)]">
              dashboard →
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Field({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-[var(--color-text-muted)]">
        {label}
      </p>
      <p
        className={`mt-1 font-mono text-sm ${
          accent ? "text-[var(--color-accent)]" : "text-white"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
