"use client";

import React from "react";
import { useTranslation, Badge, Button, Card, CardHeader, CardTitle, CardContent } from "@vigil/ui";
import { PatientResponse, ObservationItem, RiskAssessmentSummary } from "@/lib/types";
import { Plus, Activity, Calendar, ShieldCheck, FileSpreadsheet, AlertTriangle } from "lucide-react";

interface PatientTimelineProps {
  patient: PatientResponse | null;
  observations: ObservationItem[];
  riskHistory: RiskAssessmentSummary[];
  selectedObservationId: string | null;
  onSelectObservation: (obs: ObservationItem) => void;
  onOpenIntake: () => void;
}

export const PatientTimeline: React.FC<PatientTimelineProps> = ({
  patient,
  observations,
  riskHistory,
  selectedObservationId,
  onSelectObservation,
  onOpenIntake,
}) => {
  const { t } = useTranslation();

  if (!patient) {
    return (
      <Card className="p-8 text-center text-slate-500">
        <Activity className="w-8 h-8 text-slate-300 mx-auto mb-2" />
        Select a patient from the triage queue to view their surveillance timeline.
      </Card>
    );
  }

  // Sort observations by specimen_collected_at descending (latest first)
  const sortedObs = [...observations].sort(
    (a, b) => new Date(b.specimen_collected_at).getTime() - new Date(a.specimen_collected_at).getTime()
  );

  return (
    <div className="space-y-4">
      {/* Patient Header Card */}
      <Card className="border-slate-200 bg-white">
        <CardContent className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-slate-100 border border-slate-300 flex items-center justify-center font-bold text-slate-800 text-sm">
              PT
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900">{patient.id}</h3>
                {patient.mrn && (
                  <span className="text-xs font-mono bg-slate-100 text-slate-700 px-2 py-0.5 rounded border border-slate-300 font-semibold">
                    MRN: {patient.mrn}
                  </span>
                )}
                <span className="text-xs font-semibold bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded-full border border-emerald-300 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" />
                  Consented
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Age: {patient.age} • Status: <span className="font-semibold capitalize text-slate-700">{patient.status}</span>
              </p>
            </div>
          </div>

          <Button onClick={onOpenIntake} size="sm" className="flex items-center gap-1.5 self-start sm:self-auto">
            <Plus className="w-4 h-4" />
            Add Observation (Intake)
          </Button>
        </CardContent>
      </Card>

      {/* Serial Observation History */}
      <Card className="border-slate-200">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Calendar className="w-5 h-5 text-emerald-700" />
              Serial Observation Timeline
            </CardTitle>
            <span className="text-xs text-slate-500 font-medium">{observations.length} record(s)</span>
          </div>
        </CardHeader>

        <CardContent>
          {sortedObs.length === 0 ? (
            <div className="text-center py-8 text-slate-500 text-sm">
              <FileSpreadsheet className="w-8 h-8 text-slate-300 mx-auto mb-2" />
              No observations recorded yet. Click &quot;Add Observation&quot; to record serial laboratory measurements.
            </div>
          ) : (
            <div className="relative pl-4 border-l-2 border-slate-200 space-y-3.5 my-2">
              {sortedObs.map((obs) => {
                const isSelected = obs.id === selectedObservationId;
                const rawQc = (obs.quality_flags as Record<string, unknown>) || {};
                const action = (rawQc.action as "abstain" | "escalate" | "needs_repeat" | "explained" | "unavailable") || "unavailable";

                return (
                  <div
                    key={obs.id}
                    onClick={() => onSelectObservation(obs)}
                    className={`relative p-3.5 rounded-lg border transition-all cursor-pointer ${
                      isSelected
                        ? "bg-emerald-50 border-emerald-500 shadow-sm ring-1 ring-emerald-500"
                        : "bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-slate-100/60"
                    }`}
                  >
                    {/* Timeline Node Icon */}
                    <div
                      className={`absolute -left-[23px] top-4 w-3 h-3 rounded-full border-2 bg-white ${
                        action === "escalate"
                          ? "border-red-600 bg-red-100"
                          : action === "abstain"
                          ? "border-slate-500 bg-slate-100"
                          : action === "needs_repeat"
                          ? "border-amber-500 bg-amber-100"
                          : "border-emerald-600 bg-emerald-100"
                      }`}
                    />

                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-slate-900">
                            {obs.analyte_code.toUpperCase()}
                          </span>
                          <span className="text-sm font-bold text-slate-800">
                            {obs.value} {obs.unit}
                          </span>
                          <Badge variant={action === "unavailable" ? "default" : action}>{action.toUpperCase()}</Badge>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                          Collected: {new Date(obs.specimen_collected_at).toLocaleDateString()} at{" "}
                          {new Date(obs.specimen_collected_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          {obs.loinc_code && <span className="ml-2 font-mono">LOINC: {obs.loinc_code}</span>}
                        </p>
                      </div>

                      <span className="text-xs font-semibold text-emerald-800 self-start sm:self-auto">
                        Inspect Adjudication &rarr;
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recurrence Risk History Card (Conformal K8) */}
      {riskHistory.length > 0 && (
        <Card className="border-slate-200">
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Activity className="w-5 h-5 text-indigo-700" />
              M3 Assessment History (synthetic model output; not clinically calibrated)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {riskHistory.map((rh) => {
                const unc = (rh.uncertainty as Record<string, any>) || {};
                const lower = typeof unc.lower === "number" ? unc.lower : null;
                const upper = typeof unc.upper === "number" ? unc.upper : null;
                return (
                  <div
                    key={rh.id}
                    className="p-3 bg-slate-50 rounded-lg border border-slate-200 flex items-center justify-between text-xs"
                  >
                    <div>
                      {rh.abstention || rh.score == null ? (
                        <span className="font-semibold text-amber-800">
                          Model abstained{rh.abstention_reason ? `: ${rh.abstention_reason.replaceAll("_", " ")}` : ""}
                        </span>
                      ) : (
                        <>
                          <span className="font-bold text-slate-800">M3 real-change component: {(rh.score * 100).toFixed(1)}%</span>
                          {lower != null && upper != null && (
                            <span className="text-slate-500 ml-2 font-mono">
                              Interval: [{(lower * 100).toFixed(1)}%, {(upper * 100).toFixed(1)}%]
                            </span>
                          )}
                        </>
                      )}
                    </div>
                    <span className="text-slate-500">{new Date(rh.assessment_date).toLocaleDateString()}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};
