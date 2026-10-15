import React from "react";

export function SyntheticBadge() {
  return (
    <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-950/70 border border-amber-600/60 text-amber-300 text-xs font-mono font-medium shadow-sm">
      <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
      <span>SYNTHETIC DEMO DATA</span>
    </div>
  );
}
