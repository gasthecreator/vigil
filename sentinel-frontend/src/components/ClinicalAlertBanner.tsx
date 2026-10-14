"use client";

import React from "react";
import { AlertTriangle, ShieldAlert, ArrowRight, CheckCircle, FileText } from "lucide-react";

interface ClinicalAlertBannerProps {
  riskScore: number;
  justificationText: string;
  patientId: string;
}

export const ClinicalAlertBanner: React.FC<ClinicalAlertBannerProps> = ({
  riskScore,
  justificationText,
  patientId,
}) => {
  const [acknowledged, setAcknowledged] = React.useState(false);

  return (
    <div className="relative overflow-hidden rounded-xl border-2 border-rose-600 bg-gradient-to-r from-rose-950/90 via-slate-900 to-rose-950/70 p-5 shadow-2xl animate-alert-glow">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div className="flex items-start space-x-4">
          <div className="p-3 rounded-lg bg-rose-600/20 border border-rose-500/50 text-rose-400 shrink-0">
            <ShieldAlert className="w-8 h-8 animate-pulse text-rose-400" />
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center gap-3 flex-wrap">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-600 text-white flex items-center gap-1 shadow-sm">
                <AlertTriangle className="w-3.5 h-3.5" /> Actionable Second-Opinion Alert
              </span>
              <span className="font-mono text-sm text-rose-300 font-semibold">
                Metastasis Risk Score: {(riskScore * 100).toFixed(1)}% (Threshold ≥ 75.0%)
              </span>
            </div>

            <p className="text-sm text-slate-100 font-medium leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-rose-900/50">
              {justificationText}
            </p>
          </div>
        </div>

        {/* Clinical Action Tray */}
        <div className="flex flex-row md:flex-col items-end gap-2 shrink-0 justify-end pt-2 md:pt-0">
          <button
            onClick={() => alert(`Escalated Patient ${patientId.slice(0, 8)} to Multidisciplinary Tumor Board.`)}
            className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-rose-600 hover:bg-rose-500 text-white shadow-md transition-all flex items-center gap-1.5"
          >
            Escalate to Tumor Board <ArrowRight className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setAcknowledged(!acknowledged)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition-all flex items-center gap-1.5 ${
              acknowledged
                ? "bg-emerald-950/80 border-emerald-600 text-emerald-300"
                : "bg-slate-800/80 hover:bg-slate-700 border-slate-700 text-slate-300"
            }`}
          >
            <CheckCircle className="w-3.5 h-3.5" />
            {acknowledged ? "Alert Acknowledged" : "Acknowledge Alert"}
          </button>
        </div>
      </div>
    </div>
  );
};
