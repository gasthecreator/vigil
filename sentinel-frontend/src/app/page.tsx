"use client";

import React, { useEffect, useState, useCallback } from "react";
import { TriageQueue } from "@/components/TriageQueue";
import { LongitudinalChart } from "@/components/LongitudinalChart";
import { IntakeForms } from "@/components/IntakeForms";
import { OrganSusceptibilityCard } from "@/components/OrganSusceptibilityCard";
import { SimulationStudio } from "@/components/SimulationStudio";
import {
  fetchTriageQueue,
  fetchPatientDetail,
  fetchPatientTrajectory,
  fetchCohortAnalytics,
} from "@/lib/api";
import {
  TriageQueueItem,
  TrajectoryPoint,
  Patient,
  CohortAnalytics,
} from "@/lib/types";
import {
  ShieldAlert,
  AlertTriangle,
  Users,
  Activity,
  HeartPulse,
  RefreshCw,
  Clock,
} from "lucide-react";

export default function SurveillanceDashboard() {
  const [triageQueue, setTriageQueue] = useState<TriageQueueItem[]>([]);
  const [selectedPatientId, setSelectedPatientId] = useState<string | null>(null);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [trajectory, setTrajectory] = useState<TrajectoryPoint[]>([]);
  const [analytics, setAnalytics] = useState<CohortAnalytics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);

  // Load all initial surveillance data
  const loadData = useCallback(async (selectId?: string) => {
    try {
      setRefreshing(true);
      const [queueData, analyticsData] = await Promise.all([
        fetchTriageQueue(),
        fetchCohortAnalytics(),
      ]);

      setTriageQueue(queueData);
      setAnalytics(analyticsData);

      // Determine selected patient
      const targetId = selectId || selectedPatientId || (queueData.length > 0 ? queueData[0].patient_id : null);

      if (targetId) {
        setSelectedPatientId(targetId);
        const [patientDetail, trajectoryData] = await Promise.all([
          fetchPatientDetail(targetId),
          fetchPatientTrajectory(targetId),
        ]);
        setSelectedPatient(patientDetail);
        setTrajectory(trajectoryData);
      }
    } catch (err) {
      console.error("Dashboard data load error:", err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [selectedPatientId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSelectPatient = async (patientId: string) => {
    setSelectedPatientId(patientId);
    try {
      const [pDetail, pTraj] = await Promise.all([
        fetchPatientDetail(patientId),
        fetchPatientTrajectory(patientId),
      ]);
      setSelectedPatient(pDetail);
      setTrajectory(pTraj);
    } catch (err) {
      console.error("Failed to select patient:", err);
    }
  };

  const handleIntakeSuccess = (newPatientId?: string) => {
    loadData(newPatientId || selectedPatientId || undefined);
  };

  return (
    <div className="space-y-6">
      {/* Cohort Surveillance KPI Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 flex items-center space-x-3 shadow-md">
          <div className="p-2.5 rounded-lg bg-sky-950/80 text-sky-400 border border-sky-800/60">
            <Users className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Total Monitored</p>
            <p className="text-xl font-bold font-mono text-white">{analytics?.total_patients ?? "—"}</p>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-rose-900/50 rounded-xl p-3.5 flex items-center space-x-3 shadow-md">
          <div className="p-2.5 rounded-lg bg-rose-950/80 text-rose-400 border border-rose-800/60">
            <ShieldAlert className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <p className="text-xs font-medium text-rose-300">Critical Alerts (≥75%)</p>
            <p className="text-xl font-bold font-mono text-rose-200">{analytics?.critical_alerts ?? "—"}</p>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-amber-900/50 rounded-xl p-3.5 flex items-center space-x-3 shadow-md">
          <div className="p-2.5 rounded-lg bg-amber-950/80 text-amber-400 border border-amber-800/60">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-amber-300">Surveillance Watch</p>
            <p className="text-xl font-bold font-mono text-amber-200">{analytics?.watch_cases ?? "—"}</p>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-emerald-900/50 rounded-xl p-3.5 flex items-center space-x-3 shadow-md">
          <div className="p-2.5 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
            <HeartPulse className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-emerald-300">Stable Surveillance</p>
            <p className="text-xl font-bold font-mono text-emerald-200">{analytics?.stable_cases ?? "—"}</p>
          </div>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3.5 flex items-center space-x-3 shadow-md">
          <div className="p-2.5 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-800/60">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <p className="text-xs font-medium text-slate-400">Cohort Mean Risk</p>
            <p className="text-xl font-bold font-mono text-white">
              {analytics ? `${(analytics.average_cohort_risk * 100).toFixed(1)}%` : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Main Grid: View 1 (Left) and View 2 & 3 (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column: View 1 - Prioritized Triage Queue */}
        <div className="lg:col-span-5 xl:col-span-4 sticky top-20">
          <TriageQueue
            queue={triageQueue}
            selectedPatientId={selectedPatientId}
            onSelectPatient={handleSelectPatient}
            onRefresh={() => loadData()}
          />
        </div>

        {/* Right Column: View 3 (Trajectory & Alerts), Organ Card, View 2 (Intake), and Simulator */}
        <div className="lg:col-span-7 xl:col-span-8 space-y-6">
          {/* Selected Patient Identity Banner */}
          {selectedPatient && (
            <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 flex flex-wrap items-center justify-between gap-3 shadow-lg">
              <div className="flex items-center space-x-3">
                <div className="h-10 w-10 rounded-xl bg-slate-800 flex items-center justify-center font-mono font-bold text-cyan-400 text-sm border border-slate-700">
                  PT
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono text-sm font-bold text-white">
                      Patient ID: {selectedPatient.id}
                    </h3>
                    <span className="text-xs px-2 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-800">
                      {selectedPatient.age} Years Old
                    </span>
                  </div>
                  <p className="text-xs text-slate-400">
                    Enrolled {new Date(selectedPatient.created_at).toLocaleDateString()} • Status: Active Surveillance
                  </p>
                </div>
              </div>

              {selectedPatient.latest_risk !== null && (
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-400">Latest Trajectory Risk:</span>
                  <span
                    className={`font-mono text-sm font-bold px-3 py-1 rounded-lg ${
                      (selectedPatient.latest_risk ?? 0) >= 0.75
                        ? "bg-rose-600 text-white animate-pulse"
                        : (selectedPatient.latest_risk ?? 0) >= 0.40
                        ? "bg-amber-950 text-amber-300 border border-amber-800"
                        : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                    }`}
                  >
                    {((selectedPatient.latest_risk ?? 0) * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          )}

          {/* View 3: Longitudinal Risk Chart with Recharts & y=0.75 Alert Threshold */}
          {selectedPatientId && (
            <LongitudinalChart
              trajectory={trajectory}
              patientId={selectedPatientId}
            />
          )}

          {/* Organ Tropism Susceptibility (Model A Output) */}
          <OrganSusceptibilityCard
            vector={selectedPatient?.baseline_profile?.target_organ_susceptibility_vector}
            subtype={
              selectedPatient?.baseline_profile?.her2_status
                ? "HER2-Enriched"
                : selectedPatient?.baseline_profile?.er_status
                ? "Luminal A (ER+/PR+)"
                : "Triple Negative"
            }
            stage={selectedPatient?.baseline_profile?.tumor_stage}
          />

          {/* View 2: Intake Forms Side-Panels */}
          <IntakeForms
            patientList={triageQueue.map((p) => ({ id: p.patient_id, age: p.age }))}
            selectedPatientId={selectedPatientId}
            onSuccess={handleIntakeSuccess}
          />

          {/* Non-Destructive What-If Simulation Studio */}
          {selectedPatientId && (
            <SimulationStudio patientId={selectedPatientId} />
          )}
        </div>
      </div>
    </div>
  );
}
