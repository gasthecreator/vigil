"use client";

import React, { useState } from "react";
import { Sparkles, ArrowRight, Activity, TrendingUp, TrendingDown } from "lucide-react";
import { simulateFutureLab } from "@/lib/api";
import { SimulationResult } from "@/lib/types";

interface SimulationStudioProps {
  patientId: string;
}

export const SimulationStudio: React.FC<SimulationStudioProps> = ({ patientId }) => {
  const [alt, setAlt] = useState<number>(35.0);
  const [ast, setAst] = useState<number>(30.0);
  const [creatinine, setCreatinine] = useState<number>(0.90);
  const [ca153, setCa153] = useState<number>(32.0);
  const [wbc, setWbc] = useState<number>(7.0);
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<SimulationResult | null>(null);

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!patientId) return;
    setLoading(true);
    try {
      const res = await simulateFutureLab(patientId, {
        alt_level: Number(alt),
        ast_level: Number(ast),
        creatinine: Number(creatinine),
        ca_15_3: Number(ca153),
        wbc_count: Number(wbc),
      });
      setResult(res);
    } catch (err: any) {
      alert("Simulation failed: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between pb-2 border-b border-slate-800">
        <div className="flex items-center space-x-2">
          <Sparkles className="w-5 h-5 text-indigo-400" />
          <h2 className="text-base font-bold text-white tracking-wide">
            Oncology Scenario Simulator (&quot;What-If&quot; Counterfactual Studio)
          </h2>
        </div>
        <span className="text-[10px] font-mono uppercase tracking-widest px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
          Non-Destructive Projection
        </span>
      </div>

      <p className="text-xs text-slate-400">
        Simulate the impact of hypothetical next-cycle biomarker levels to evaluate risk velocity prior
        to actual clinical blood draw.
      </p>

      <form onSubmit={handleSimulate} className="space-y-4">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Hypothetical ALT</label>
            <input
              type="number"
              step="0.1"
              value={alt}
              onChange={(e) => setAlt(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Hypothetical AST</label>
            <input
              type="number"
              step="0.1"
              value={ast}
              onChange={(e) => setAst(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">Creatinine</label>
            <input
              type="number"
              step="0.01"
              value={creatinine}
              onChange={(e) => setCreatinine(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-indigo-300">Hypothetical CA 15-3</label>
            <input
              type="number"
              step="0.1"
              value={ca153}
              onChange={(e) => setCa153(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-indigo-800 rounded-lg px-2.5 py-1.5 text-xs text-indigo-300 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-xs font-semibold text-slate-300">WBC Count</label>
            <input
              type="number"
              step="0.1"
              value={wbc}
              onChange={(e) => setWbc(parseFloat(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-2"
        >
          {loading ? "Computing Counterfactual..." : "Run Scenario Simulation"}
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </form>

      {result && (
        <div className="p-4 rounded-xl bg-slate-950 border border-indigo-900/60 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-indigo-300">Simulated Trajectory Outcome:</span>
            <div className="flex items-center gap-3">
              <span className="font-mono text-sm font-bold text-white">
                Projected Risk: {(result.projected_risk * 100).toFixed(1)}%
              </span>
              <span
                className={`text-xs font-mono font-bold px-2 py-0.5 rounded flex items-center gap-1 ${
                  result.delta_risk >= 0
                    ? "bg-rose-950 text-rose-300 border border-rose-800"
                    : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                }`}
              >
                {result.delta_risk >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {result.delta_risk >= 0 ? "+" : ""}
                {(result.delta_risk * 100).toFixed(1)}% Delta
              </span>
            </div>
          </div>
          <p className="text-xs text-slate-300 leading-relaxed font-mono">
            {result.justification_text}
          </p>
        </div>
      )}
    </div>
  );
};
