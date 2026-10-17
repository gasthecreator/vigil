import React from "react";
import { AlertTriangle } from "lucide-react";

export function ClinicalDisclaimer() {
  return (
    <footer className="mt-12 p-4 rounded-lg bg-slate-900 border border-slate-800 text-xs text-slate-200 space-y-2">
      <div className="flex items-start gap-2.5">
        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <p className="font-semibold text-white">
            MANDATORY CLINICAL & RESEARCH NOTICE
          </p>
          <p className="text-slate-200">
            Vigil is a research prototype and clinical decision-support aid. It is <strong className="font-bold text-white">not</strong> a medical device,
            does <strong className="font-bold text-white">not</strong> diagnose or treat any condition, and must <strong className="font-bold text-white">not</strong> replace the clinical
            judgement of a qualified healthcare professional. All risk trajectories and scores are currently demonstrated
            on synthetic and research benchmark cohorts.
          </p>
          <p className="text-slate-300">
            If you or a patient experience acute severe symptoms (dyspnea, sudden swelling, jaundice, severe pain),
            refer immediately to the nearest hospital emergency department.
          </p>
        </div>
      </div>
    </footer>
  );
}
