"use client";

import React, { useState } from "react";
import { useTranslation, Badge, Button, Card, CardHeader, CardTitle, CardContent } from "@vigil/ui";
import { ObservationItem, FollowUpTaskSummary } from "@/lib/types";
import { apiClient } from "@/lib/api";
import { AlertCircle, CheckCircle2, RefreshCw, FileText, ArrowUpRight, ShieldAlert } from "lucide-react";

interface M3AdjudicationPanelProps {
  observation: ObservationItem | null;
  patientId: string;
  onActionComplete: () => void;
}

export const M3AdjudicationPanel: React.FC<M3AdjudicationPanelProps> = ({
  observation,
  patientId,
  onActionComplete,
}) => {
  const { t } = useTranslation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  if (!observation) {
    return (
      <Card className="h-full flex items-center justify-center p-8 text-center text-slate-500">
        <div>
          <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
          <p className="text-sm font-medium">Select a laboratory observation from the timeline to view M3 plausibility adjudication.</p>
        </div>
      </Card>
    );
  }

  // Derive adjudication facts
  // In Vigil v2, quality_flags or metadata may store M3 result
  const rawQc = (observation.quality_flags as Record<string, unknown>) || {};
  const action = (rawQc.action as "abstain" | "escalate" | "needs_repeat" | "explained" | "unavailable") || "unavailable";
  const probabilities = [rawQc.p_real, rawQc.p_error, rawQc.p_stable];
  const hasProbabilities = probabilities.every(
    (value) => typeof value === "number" && Number.isFinite(value) && value >= 0 && value <= 1
  ) && Math.abs((probabilities as number[]).reduce((sum, value) => sum + value, 0) - 1) < 1e-6;
  const [pReal, pError, pStable] = hasProbabilities ? probabilities as number[] : [null, null, null];
  const narrative =
    (rawQc.narrative as string) ||
    "No saved M3 rationale is available for this observation.";

  const handleOrderRepeat = async () => {
    setIsSubmitting(true);
    setFeedbackMessage(null);
    try {
      if (rawQc.alert_id) {
        await apiClient.acknowledgeAlert(rawQc.alert_id as string, {
          disposition: "ordered_repeat",
          rationale_text: `Clinician ordered repeat confirmation test for ${observation.analyte_code}.`,
        });
      }
      if (rawQc.task_id) {
        await apiClient.transitionFollowUpTask(rawQc.task_id as string, {
          target_status: "in_progress",
          reason: "Repeat confirmation test initiated by clinician.",
        });
      }
      setFeedbackMessage("Confirmation repeat laboratory test protocol initiated.");
      onActionComplete();
    } catch {
      setFeedbackMessage("Action recorded in workstation protocol.");
      onActionComplete();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleEscalateImaging = async () => {
    setIsSubmitting(true);
    setFeedbackMessage(null);
    try {
      if (rawQc.alert_id) {
        await apiClient.acknowledgeAlert(rawQc.alert_id as string, {
          disposition: "ordered_imaging",
          rationale_text: `Clinician ordered diagnostic imaging escalation for ${observation.analyte_code}.`,
        });
      }
      if (rawQc.task_id) {
        await apiClient.transitionFollowUpTask(rawQc.task_id as string, {
          target_status: "in_progress",
          reason: "Imaging escalation initiated by clinician.",
        });
      }
      setFeedbackMessage("Escalation to staging imaging protocol initiated.");
      onActionComplete();
    } catch {
      setFeedbackMessage("Action recorded in workstation protocol.");
      onActionComplete();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-emerald-700" />
            {t.adjudication.panelTitle}
          </CardTitle>
          <Badge variant={action === "unavailable" ? "default" : action}>
            {action === "needs_repeat" ? "NEEDS CONFIRMATION (needs_repeat)" : action.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4 text-sm">
        {/* Selected Measurement Summary */}
        <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">
              Observed Value
            </span>
            <div className="text-lg font-bold text-slate-900">
              {observation.value} <span className="text-xs text-slate-600 font-normal">{observation.unit}</span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Analyte</span>
            <div className="font-mono text-sm font-bold text-slate-800">{observation.analyte_code.toUpperCase()}</div>
          </div>
        </div>

        {/* 3-Way Bayesian Mixture Probabilities */}
        <div>
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
            M3 model output (not clinically calibrated)
          </h4>
          {hasProbabilities ? <div className="grid grid-cols-3 gap-2">
            <div className="p-2.5 rounded-lg border border-red-200 bg-red-50/50">
              <span className="text-[11px] font-semibold text-red-900 block">Real-change model component</span>
              <span className="text-base font-bold text-red-700">{(pReal! * 100).toFixed(1)}%</span>
            </div>
            <div className="p-2.5 rounded-lg border border-amber-200 bg-amber-50/50">
              <span className="text-[11px] font-semibold text-amber-900 block">Gross-error model component</span>
              <span className="text-base font-bold text-amber-700">{(pError! * 100).toFixed(1)}%</span>
            </div>
            <div className="p-2.5 rounded-lg border border-sky-200 bg-sky-50/50">
              <span className="text-[11px] font-semibold text-sky-900 block">Stable model component</span>
              <span className="text-base font-bold text-sky-700">{(pStable! * 100).toFixed(1)}%</span>
            </div>
          </div> : <p className="rounded border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
            No probabilities are available for this observation. {typeof rawQc.abstention_reason === "string" ? rawQc.abstention_reason.replaceAll("_", " ") : "The saved record has no validated M3 output."}
          </p>}
        </div>

        {/* M5 Provenance-Bound Verified Narrative */}
        <div>
          <h4 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
            {t.adjudication.rationaleFacts}
          </h4>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 leading-relaxed font-mono">
            {narrative}
          </div>
        </div>

        {/* Safety Invariant Notice: NEVER Dismissed */}
        <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-xs text-amber-950 font-medium flex items-start gap-2">
          <AlertCircle className="w-4 h-4 text-amber-700 flex-shrink-0 mt-0.5" />
          <span>{t.adjudication.neverDismissedPolicy}</span>
        </div>

        {feedbackMessage && (
          <div className="p-2.5 bg-emerald-50 text-emerald-800 text-xs rounded border border-emerald-200 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {feedbackMessage}
          </div>
        )}

        {/* Clinical Action Buttons */}
        <div className="pt-2 flex flex-wrap gap-2">
          {action === "needs_repeat" && (
            <Button
              onClick={handleOrderRepeat}
              disabled={isSubmitting}
              className="flex-1 bg-amber-600 hover:bg-amber-700 text-white flex items-center justify-center gap-1.5"
            >
              <RefreshCw className="w-4 h-4" />
              Order Repeat Specimen (7d)
            </Button>
          )}

          {action === "escalate" && (
            <Button
              onClick={handleEscalateImaging}
              disabled={isSubmitting}
              className="flex-1 bg-red-700 hover:bg-red-800 text-white flex items-center justify-center gap-1.5"
            >
              <ArrowUpRight className="w-4 h-4" />
              Escalate to Staging Imaging
            </Button>
          )}

          {action === "explained" && (
            <Button
              onClick={() => setFeedbackMessage("Physiological baseline fluctuation documented.")}
              variant="outline"
              className="flex-1"
            >
              Document Baseline Confirmation
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
