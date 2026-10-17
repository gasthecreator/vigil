"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useTranslation, Button } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import {
  PatientResponse,
  ObservationItem,
  RiskAssessmentSummary,
  AlertSummary,
  FollowUpTaskResponse,
  TriagePatientViewModel,
} from "@/lib/types";
import { TriageQueue } from "@/components/TriageQueue";
import { PatientTimeline } from "@/components/PatientTimeline";
import { M3AdjudicationPanel } from "@/components/M3AdjudicationPanel";
import { AlertInbox } from "@/components/AlertInbox";
import { FollowUpBoard } from "@/components/FollowUpBoard";
import { ObservationIntakeModal } from "@/components/ObservationIntakeModal";
import { PatientEnrollmentModal } from "@/components/PatientEnrollmentModal";
import { Users, Bell, CheckSquare, RefreshCw } from "lucide-react";

export default function ClinicianWorkstation() {
  const { t } = useTranslation();

  // Navigation Tabs
  const [activeTab, setActiveTab] = useState<"triage" | "alerts" | "followup">("triage");

  // Core Data State
  const [patients, setPatients] = useState<PatientResponse[]>([]);
  const [alerts, setAlerts] = useState<AlertSummary[]>([]);
  const [followUpTasks, setFollowUpTasks] = useState<FollowUpTaskResponse[]>([]);

  // Selected Patient State
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<PatientResponse | null>(null);
  const [observations, setObservations] = useState<ObservationItem[]>([]);
  const [riskHistory, setRiskHistory] = useState<RiskAssessmentSummary[]>([]);
  const [selectedObservation, setSelectedObservation] = useState<ObservationItem | null>(null);

  // Modals
  const [isEnrollmentOpen, setIsEnrollmentOpen] = useState(false);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);

  // Loading & Feedback
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load all initial data from Vigil API client
  const loadWorkstationData = useCallback(async (preferredPatientId?: string) => {
    try {
      setIsRefreshing(true);
      const [ptsData, alertsData, tasksData] = await Promise.all([
        apiClient.listPatients().catch(() => []),
        apiClient.listAlerts("open").catch(() => []),
        apiClient.getOutreachList().catch(() => []),
      ]);

      setPatients(ptsData);
      setAlerts(alertsData);
      setFollowUpTasks(tasksData);

      const targetId = preferredPatientId || selectedPatientId || (ptsData.length > 0 ? ptsData[0].id : null);
      if (targetId) {
        setSelectedPatientId(targetId);
        await loadPatientDetails(targetId);
      }
    } catch (err) {
      console.error("Failed to load workstation data:", err);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedPatientId]);

  const loadPatientDetails = async (patientId: string) => {
    try {
      const [pt, obsList, rHistory] = await Promise.all([
        apiClient.getPatient(patientId),
        apiClient.listObservations(patientId).catch(() => []),
        apiClient.listRiskHistory(patientId).catch(() => []),
      ]);
      setSelectedPatient(pt);
      setObservations(obsList);
      setRiskHistory(rHistory);

      // Default select latest observation if present
      if (obsList.length > 0) {
        const sorted = [...obsList].sort(
          (a, b) => new Date(b.specimen_collected_at).getTime() - new Date(a.specimen_collected_at).getTime()
        );
        setSelectedObservation(sorted[0]);
      } else {
        setSelectedObservation(null);
      }
    } catch (err) {
      console.error(`Failed to load details for patient ${patientId}:`, err);
    }
  };

  useEffect(() => {
    loadWorkstationData();
  }, [loadWorkstationData]);

  const handleSelectPatient = async (patientId: string) => {
    setSelectedPatientId(patientId);
    await loadPatientDetails(patientId);
  };

  // Compute composite urgency view-models for triage queue
  const triageViewModels: TriagePatientViewModel[] = (Array.isArray(patients) ? patients : []).map((pt) => {
    const ptTasks = followUpTasks.filter((t) => t.patient_id === pt.id && t.status !== "completed");
    const ptAlerts = alerts.filter((a) => a.id.includes(pt.id));
    const isSelected = pt.id === selectedPatientId;
    const ptObs = isSelected ? observations : [];
    const latestObs = ptObs.length > 0 ? ptObs[0] : null;

    // Composite urgency calculation:
    // Risk weight + active alert weight + task weight
    let urgencyScore = 20; // baseline
    if (ptTasks.length > 0) urgencyScore += Math.min(ptTasks.length * 15, 45);
    if (ptAlerts.length > 0) urgencyScore += 35;
    if (latestObs) {
      const qc = (latestObs.quality_flags as Record<string, unknown>) || {};
      if (qc.action === "escalate") urgencyScore += 40;
      else if (qc.action === "needs_repeat") urgencyScore += 25;
    }

    let urgencyLevel: "urgent" | "high" | "medium" | "low" = "low";
    if (urgencyScore >= 75) urgencyLevel = "urgent";
    else if (urgencyScore >= 50) urgencyLevel = "high";
    else if (urgencyScore >= 30) urgencyLevel = "medium";

    const qcFlags = (latestObs?.quality_flags as Record<string, unknown>) || {};

    return {
      id: pt.id,
      mrn: pt.mrn,
      age: pt.age,
      status: pt.status,
      compositeUrgencyScore: urgencyScore,
      urgencyLevel,
      latestAnalyteCode: latestObs?.analyte_code || null,
      latestAnalyteValue: latestObs?.value || null,
      latestAnalyteUnit: latestObs?.unit || null,
      latestM3Action: (qcFlags.action as any) || null,
      openTasksCount: ptTasks.length,
      openAlertsCount: ptAlerts.length,
      daysSinceLastVisit: 14,
    };
  });

  return (
    <div className="space-y-6">
      {/* Top Navigation Tabs & Feed Refresh */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-3">
        <div className="flex items-center gap-2" role="tablist">
          <button
            role="tab"
            aria-selected={activeTab === "triage"}
            onClick={() => setActiveTab("triage")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
              activeTab === "triage"
                ? "bg-emerald-700 text-white shadow-sm"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <Users className="w-4 h-4" />
            Triage & Surveillance
          </button>

          <button
            role="tab"
            aria-selected={activeTab === "alerts"}
            onClick={() => setActiveTab("alerts")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
              activeTab === "alerts"
                ? "bg-emerald-700 text-white shadow-sm"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <Bell className="w-4 h-4" />
            Alert Inbox
            {alerts.length > 0 && (
              <span className="bg-red-500 text-white text-[11px] px-1.5 py-0.2 rounded-full font-mono">
                {alerts.length}
              </span>
            )}
          </button>

          <button
            role="tab"
            aria-selected={activeTab === "followup"}
            onClick={() => setActiveTab("followup")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-bold transition-all ${
              activeTab === "followup"
                ? "bg-emerald-700 text-white shadow-sm"
                : "bg-white text-slate-700 hover:bg-slate-100 border border-slate-200"
            }`}
          >
            <CheckSquare className="w-4 h-4" />
            Follow-Up Guardian (M6)
            {followUpTasks.length > 0 && (
              <span className="bg-amber-500 text-white text-[11px] px-1.5 py-0.2 rounded-full font-mono">
                {followUpTasks.length}
              </span>
            )}
          </button>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={() => loadWorkstationData()}
          disabled={isRefreshing}
          className="flex items-center gap-1.5 self-start sm:self-auto text-xs"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          {t.common.refresh}
        </Button>
      </div>

      {/* Main Tab Views */}
      {activeTab === "triage" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Triage Queue (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <TriageQueue
              patients={triageViewModels}
              selectedPatientId={selectedPatientId}
              onSelectPatient={handleSelectPatient}
              onOpenEnrollment={() => setIsEnrollmentOpen(true)}
            />
          </div>

          {/* Right Column: Timeline & M3 Adjudication (7 cols) */}
          <div className="lg:col-span-7 space-y-6">
            <PatientTimeline
              patient={selectedPatient}
              observations={observations}
              riskHistory={riskHistory}
              selectedObservationId={selectedObservation?.id || null}
              onSelectObservation={(obs) => setSelectedObservation(obs)}
              onOpenIntake={() => setIsIntakeOpen(true)}
            />

            <M3AdjudicationPanel
              observation={selectedObservation}
              patientId={selectedPatientId || ""}
              onActionComplete={() => loadWorkstationData(selectedPatientId || undefined)}
            />
          </div>
        </div>
      )}

      {activeTab === "alerts" && (
        <AlertInbox alerts={alerts} onAcknowledgeSuccess={() => loadWorkstationData()} />
      )}

      {activeTab === "followup" && (
        <FollowUpBoard tasks={followUpTasks} onTaskUpdated={() => loadWorkstationData()} />
      )}

      {/* Observation Intake Modal (Alt+S enabled) */}
      {selectedPatientId && (
        <ObservationIntakeModal
          isOpen={isIntakeOpen}
          onClose={() => setIsIntakeOpen(false)}
          patientId={selectedPatientId}
          onIntakeSuccess={() => loadPatientDetails(selectedPatientId)}
        />
      )}

      {/* Patient Enrollment Modal (Journey J1) */}
      <PatientEnrollmentModal
        isOpen={isEnrollmentOpen}
        onClose={() => setIsEnrollmentOpen(false)}
        onEnrollmentSuccess={(newId) => loadWorkstationData(newId)}
      />
    </div>
  );
}
