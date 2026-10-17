"use client";

import React, { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslation, Button, Card, Badge, SyntheticBanner } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import {
  PatientResponse,
  ObservationItem,
  RiskAssessmentSummary,
} from "@/lib/types";
import { PatientTimeline } from "@/components/PatientTimeline";
import { M3AdjudicationPanel } from "@/components/M3AdjudicationPanel";
import { ObservationIntakeModal } from "@/components/ObservationIntakeModal";
import { ArrowLeft, Plus, RefreshCw, Calendar, FileText } from "lucide-react";

export default function PatientTimelinePage() {
  const params = useParams();
  const patientId = params?.id as string;
  const { t } = useTranslation();

  const [patient, setPatient] = useState<PatientResponse | null>(null);
  const [observations, setObservations] = useState<ObservationItem[]>([]);
  const [riskHistory, setRiskHistory] = useState<RiskAssessmentSummary[]>([]);
  const [selectedObservation, setSelectedObservation] = useState<ObservationItem | null>(null);
  const [isIntakeOpen, setIsIntakeOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!patientId) return;
    setIsLoading(true);
    setError(null);
    try {
      const [pt, obs, risks] = await Promise.all([
        apiClient.getPatient(patientId),
        apiClient.listObservations(patientId),
        apiClient.listRiskHistory(patientId),
      ]);
      setPatient(pt);
      setObservations(obs);
      setRiskHistory(risks);
      if (obs && obs.length > 0) {
        setSelectedObservation(obs[0]);
      }
    } catch (err: any) {
      console.error("Failed to load patient timeline:", err);
      setError(err?.message || "Failed to load patient timeline data.");
    } finally {
      setIsLoading(false);
    }
  }, [patientId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col">
      <SyntheticBanner />

      {/* Navigation & Patient Header */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 shadow-sm">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors px-2.5 py-1.5 rounded-md hover:bg-slate-100"
              aria-label="Back to Triage Queue"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Back to Triage</span>
            </Link>
            <div className="h-5 w-px bg-slate-200" />
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-slate-900">
                  {patient?.id || patientId}
                </h1>
                <Badge variant={patient?.status === "active" ? "success" : "default"}>
                  {patient?.status || "active"}
                </Badge>
                <Badge variant="warning">Synthetic</Badge>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                MRN: {patient?.mrn || "Protected"} • Age: {patient?.age ?? "N/A"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              variant="outline"
              size="sm"
              onClick={loadData}
              disabled={isLoading}
              aria-label="Refresh timeline data"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => setIsIntakeOpen(true)}
              aria-label="New Lab Observation Intake"
            >
              <Plus className="w-3.5 h-3.5 mr-1.5" />
              New Observation
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {error && (
          <div className="p-4 bg-red-50 border border-red-200 text-red-800 rounded-lg text-sm">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="p-12 text-center text-slate-500">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-slate-400" />
            <p className="text-sm font-medium">Loading patient longitudinal surveillance history...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Interactive Longitudinal Timeline */}
            <div className="lg:col-span-2 space-y-6">
              <PatientTimeline
                patient={patient}
                observations={observations}
                riskHistory={riskHistory}
                selectedObservationId={selectedObservation?.id || null}
                onSelectObservation={(obs) => setSelectedObservation(obs)}
                onOpenIntake={() => setIsIntakeOpen(true)}
              />
            </div>

            {/* Right Col: M3 Plausibility Adjudication Panel */}
            <div className="space-y-6">
              <M3AdjudicationPanel
                patientId={patientId}
                observation={selectedObservation}
                onActionComplete={loadData}
              />
            </div>
          </div>
        )}
      </main>

      {/* Observation Intake Modal */}
      {patient && (
        <ObservationIntakeModal
          isOpen={isIntakeOpen}
          patientId={patient.id}
          onClose={() => setIsIntakeOpen(false)}
          onIntakeSuccess={() => {
            setIsIntakeOpen(false);
            loadData();
          }}
        />
      )}
    </div>
  );
}
