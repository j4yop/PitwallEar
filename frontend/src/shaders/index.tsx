// Local bridge to the canonical ThreeUI `StructureFlowCollection`.
// Only the Flux Vortex variant is enabled in this build (matches the brief).
// The full EFFECTS registry lives in NeuformBatchEffects.tsx alongside the
// canonical component source; it would need the other 16 .html sources to
// compile, which aren't part of this bundle.

import type { CSSProperties } from "react";
import { FluxVortex, type NeuformBatchEffectProps } from "./neuform-isolated/NeuformBatchEffects";
import "@/shaders/threeui.css";

type Props = NeuformBatchEffectProps & {
  className?: string;
  style?: CSSProperties;
  children?: React.ReactNode;
};

export function StructureFlowCollection({ className, style, children, ...props }: Props) {
  return (
    <div
      className={className ?? "shader-frame"}
      style={{ position: "absolute", inset: 0, ...style }}
    >
      <FluxVortex {...props} />
      {children}
    </div>
  );
}

export default StructureFlowCollection;
