"use client";

import React from "react";
import { TargetOrganVector } from "@/lib/types";
import { Target, Activity } from "lucide-react";

interface OrganSusceptibilityCardProps {
  vector?: TargetOrganVector | null;
  subtype?: string;
  stage?: number | null;
}

export const OrganSusceptibilityCard: React.FC<OrganSusceptibilityCardProps> = ({
  vector,
  subtype,
  stage,
}) => {
  if (!vector) {
    return (
      <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-center">
        <Target className="w-8 h-8 text-slate-600 mx-auto mb-2" />
        <p className="text-xs text-slate-400">Baseline pathology profile not yet submitted.</p>
      </div>
    );
  }

  const organs = [
    { name: "Bone", key: "bone", val: vector.bone, color: "bg-amber-500", text: "text-amber-400" },
    { name: "Liver", key: "liver", val: vector.liver, color: "bg-rose-500", text: "text-rose-400" },
    { name: "Lung", key: "lung", val: vector.lung, color: "bg-sky-500", text: "text-sky-400" },
    { name: "Brain", key: "brain", val: vector.brain, color: "bg-purple-500", text: "text-purple-400" },
  ];

  // Find dominant predilection
  const primary = [...organs].sort((a, b) => b.val - a.val)[0];

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Target className="w-4 h-4 text-cyan-400" />
          <h3 className="text-xs font-semibold text-slate-200 uppercase tracking-wider">
            Model A: Target Organ Tropism
          </h3>
        </div>
        <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/60 border border-cyan-800/40 px-2 py-0.5 rounded">
          Dominant: {primary.name} ({(primary.val * 100).toFixed(0)}%)
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 pt-1">
        {organs.map((org) => {
          const pct = Math.round(org.val * 100);
          return (
            <div key={org.key} className="space-y-1 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
              <div className="flex justify-between items-center text-xs">
                <span className="text-slate-300 font-medium">{org.name}</span>
                <span className={`font-mono font-bold ${org.text}`}>{pct}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className={`h-full ${org.color} rounded-full transition-all duration-500`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="text-[11px] text-slate-400 leading-tight">
        Calibrated XGBoost prior conditioned on Stage {stage || "II"}, {subtype || "Invasive Breast Carcinoma"}.
      </p>
    </div>
  );
};
