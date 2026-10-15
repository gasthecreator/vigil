import type { Metadata } from "next";
import "./globals.css";
import { SyntheticBadge } from "@/components/SyntheticBadge";
import { ClinicalDisclaimer } from "@/components/ClinicalDisclaimer";

export const metadata: Metadata = {
  title: "Vigil | Continuous Multimodal Oncology Surveillance",
  description: "Evidence-disciplined decision-support platform for breast cancer surveillance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen flex flex-col antialiased selection:bg-cyan-500 selection:text-white">
        {/* Clinical Top Navigation Bar */}
        <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between shadow-lg">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-2.5">
              <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-cyan-600 via-sky-500 to-indigo-500 flex items-center justify-center shadow-md shadow-cyan-500/20">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <span className="font-bold text-lg tracking-wider text-white flex items-center gap-2">
                  VIGIL
                  <span className="text-[10px] uppercase font-mono tracking-widest px-2 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800/60">
                    Decision Support Aid
                  </span>
                </span>
                <p className="text-xs text-slate-400 font-medium">Continuous Multimodal Oncology Surveillance</p>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4 text-xs">
            {/* Synthetic Data Badge */}
            <SyntheticBadge />

            {/* Alert Threshold Indicator */}
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-rose-950/50 border border-rose-800/60 text-rose-300">
              <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
              <span className="font-mono font-medium">Alert Cutoff: <strong className="text-rose-200">y ≥ 0.75</strong></span>
            </div>

            {/* Model Engine Status */}
            <div className="flex items-center space-x-2 px-3 py-1.5 rounded-md bg-slate-800/80 border border-slate-700/80 text-slate-300">
              <span className="h-2 w-2 rounded-full bg-amber-400" />
              <span className="font-medium">Model Status: <span className="text-amber-300 font-mono">Quarantined (Research)</span></span>
            </div>
          </div>
        </header>

        {/* Main Application Area */}
        <main className="flex-1 p-6 max-w-7xl w-full mx-auto space-y-6">
          {children}
          <ClinicalDisclaimer />
        </main>
      </body>
    </html>
  );
}
