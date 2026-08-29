// Centralized lucide icon re-exports so Landing.tsx doesn't import the
// whole library directly. The installed lucide-react version doesn't
// export all of the names we need; this file is the one place to remap.
import {
  Radio,
  Gauge,
  Brain,
  Activity,
  Sparkles,
  Cpu,
  LineChart,
  ShieldCheck,
  Zap,
  ArrowRight,
  Check,
  Mic,
  FileText,
  Play,
  Terminal,
  Waves,
  CircuitBoard,
  Sigma,
  GitBranch,
  Clock,
  BookOpen,
  ExternalLink,
} from "lucide-react";

export const LucideRadio = Radio;
export const LucideGauge = Gauge;
export const LucideBrain = Brain;
export const LucideActivity = Activity;
export const LucideSparkles = Sparkles;
export const LucideCpu = Cpu;
export const LucideLineChart = LineChart;
export const LucideShieldCheck = ShieldCheck;
export const LucideZap = Zap;
export const LucideArrowRight = ArrowRight;
export const LucideCheck = Check;
export const LucideMic = Mic;
export const LucideFileText = FileText;
export const LucidePlay = Play;
export const LucideTerminal = Terminal;
export const LucideWaves = Waves;
export const LucideCircuitBoard = CircuitBoard;
export const LucideSigma = Sigma;
export const LucideGitBranch = GitBranch;
export const LucideClock = Clock;
export const LucideBookOpen = BookOpen;
export const LucideExternalLink = ExternalLink;
