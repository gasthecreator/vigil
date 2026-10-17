/**
 * packages/ui/src/tokens/index.ts
 *
 * Design Tokens for Vigil Oncology Clinical Interface.
 * Designed for WCAG 2.2 AA/AAA compliance, minimum 4.5:1 text contrast,
 * minimum 44x44px interactive tap targets, and clear status distinctions.
 */

export const colors = {
  // Brand & Foundation
  brand: {
    50: "#f0fdf4",
    100: "#dcfce7",
    200: "#bbf7d0",
    500: "#22c55e",
    600: "#16a34a",
    700: "#15803d",
    800: "#166534",
    900: "#14532d",
    950: "#052e16",
  },
  // Neutral Surfaces (Slate)
  neutral: {
    50: "#f8fafc",
    100: "#f1f5f9",
    200: "#e2e8f0",
    300: "#cbd5e1",
    400: "#94a3b8",
    500: "#64748b",
    600: "#475569",
    700: "#334155",
    800: "#1e293b",
    900: "#0f172a",
    950: "#020617",
  },
  // M3 Plausibility Actions (NEVER "dismissed")
  plausibility: {
    escalate: {
      bg: "#fee2e2",
      text: "#991b1b",
      border: "#f87171",
      badge: "bg-red-100 text-red-900 border-red-300",
      description: "True disease progression likely (p_real >= 0.60). Immediate clinical review & imaging ladder.",
    },
    needs_repeat: {
      bg: "#fef3c7",
      text: "#92400e",
      border: "#fcd34d",
      badge: "bg-amber-100 text-amber-900 border-amber-300",
      description: "Possible analytical / pre-analytical error or borderline change. Laboratory re-test recommended.",
    },
    explained: {
      bg: "#e0f2fe",
      text: "#075985",
      border: "#7dd3fc",
      badge: "bg-sky-100 text-sky-900 border-sky-300",
      description: "Within personalized reference change value (RCV) and within-subject biological fluctuation.",
    },
  },
  // Sequential Alert Tiers (Ville's Martingale K2)
  alertTiers: {
    urgent: {
      label: "Urgent Review",
      color: "#b91c1c",
      badge: "bg-red-100 text-red-900 border border-red-400 font-bold",
      alpha: 0.01,
      description: "Anytime-valid e-value crossed alpha=0.01. Confirmed trend warrants expedited clinical evaluation.",
    },
    review: {
      label: "Clinical Review",
      color: "#b45309",
      badge: "bg-amber-100 text-amber-900 border border-amber-400 font-semibold",
      alpha: 0.05,
      description: "Anytime-valid e-value crossed alpha=0.05. Persistent elevation warrants clinician assessment.",
    },
    watch: {
      label: "Watch List",
      color: "#0369a1",
      badge: "bg-sky-100 text-sky-900 border border-sky-400 font-semibold",
      alpha: 0.20,
      description: "Early kinetic deviation detected. Suggest earlier interval re-test.",
    },
  },
  // Synthetic Data Provenance (Mandatory Reality Guarantee)
  synthetic: {
    bg: "#fef9c3",
    text: "#854d0e",
    border: "#facc15",
    banner: "bg-yellow-300 text-yellow-950 font-bold border-b-2 border-yellow-600",
  },
};

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    mono: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
  },
  fontSize: {
    xs: ["0.75rem", { lineHeight: "1rem" }],
    sm: ["0.875rem", { lineHeight: "1.25rem" }],
    base: ["1rem", { lineHeight: "1.5rem" }],
    lg: ["1.125rem", { lineHeight: "1.75rem" }],
    xl: ["1.25rem", { lineHeight: "1.75rem" }],
    "2xl": ["1.5rem", { lineHeight: "2rem" }],
  },
};

export const touchTargets = {
  minSize: "44px", // WCAG 2.2 AAA target size
};
