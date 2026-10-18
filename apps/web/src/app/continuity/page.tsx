"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useTranslation, Button } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import {
  LinacMachineResponse,
  RadiotherapyCourseResponse,
  ScheduleSolveResponse,
  ScheduleAssignment,
  DelayLedgerEntryResponse,
} from "@/lib/types";
import {
  Zap,
  Activity,
  Calendar,
  AlertTriangle,
  CheckCircle,
  Clock,
  ShieldCheck,
  RefreshCw,
  Cpu,
  Layers,
  ArrowRight,
  TrendingUp,
} from "lucide-react";

export default function ContinuityPage() {
  const { t } = useTranslation();

  // State
  const [machines, setMachines] = useState<LinacMachineResponse[]>([]);
  const [courses, setCourses] = useState<RadiotherapyCourseResponse[]>([]);
  const [ledger, setLedger] = useState<DelayLedgerEntryResponse[]>([]);
  const [solveResult, setSolveResult] = useState<ScheduleSolveResponse | null>(null);

  // Loading & Action states
  const [isLoading, setIsLoading] = useState(true);
  const [isSolving, setIsSolving] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [confirmSuccess, setConfirmSuccess] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Solver Parameters
  const [horizonDays, setHorizonDays] = useState<number>(14);
  const [fairnessBound, setFairnessBound] = useState<number>(5.0);
  const [maxWaitDays, setMaxWaitDays] = useState<number>(30);
  // ADR-0019: the explainable urgency ranking is the default; CP-SAT is an opt-in research module.
  const [method, setMethod] = useState<"urgency_ranking" | "cpsat_research">("urgency_ranking");

  // Active Tab
  const [activeTab, setActiveTab] = useState<"scheduler" | "courses" | "machines" | "ledger">("scheduler");

  // Load all initial data
  const loadContinuityData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [machinesData, coursesData, ledgerData] = await Promise.all([
        apiClient.listLinacMachines().catch(() => []),
        apiClient.listRadiotherapyCourses().catch(() => []),
        apiClient.getDelayLedger().catch(() => []),
      ]);
      setMachines(machinesData);
      setCourses(coursesData);
      setLedger(ledgerData);
    } catch (err) {
      console.error("Failed to load continuity data:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadContinuityData();
  }, [loadContinuityData]);

  // Handle Machine Status Update
  const handleToggleMachineStatus = async (machine: LinacMachineResponse) => {
    try {
      const newStatus = machine.status === "operational" ? "down" : "operational";
      await apiClient.updateMachineStatus(machine.id, {
        status: newStatus,
        reason: newStatus === "down" ? "Reported unexpected beam fault" : "Service restored and calibrated",
      });
      setStatusMessage(`Machine ${machine.machine_name} updated to ${newStatus}.`);
      await loadContinuityData();
    } catch (err) {
      console.error("Failed to update machine status:", err);
      setStatusMessage("Failed to update machine status.");
    }
  };

  // Propose a schedule with the selected method
  const handleSolveSchedule = async () => {
    try {
      setIsSolving(true);
      setConfirmSuccess(null);
      const res = await apiClient.solveSchedule({
        method,
        horizon_days: horizonDays,
        fairness_disparity_bound: fairnessBound,
        max_wait_days: maxWaitDays,
        stability_penalty: 0.01,
      });
      setSolveResult(res);
      setStatusMessage(`${res.method_label ?? "Schedule"}: ${res.assignments.length} assignments proposed in ${res.solver_time_seconds}s.`);
    } catch (err) {
      console.error("Failed to solve schedule:", err);
      setStatusMessage(
        method === "cpsat_research"
          ? "Failed to solve schedule. The CP-SAT research optimiser is available to administrators only."
          : "Failed to solve schedule.",
      );
    } finally {
      setIsSolving(false);
    }
  };

  // Clinician Confirm Schedule
  const handleConfirmSchedule = async () => {
    if (!solveResult || solveResult.assignments.length === 0) return;
    try {
      setIsConfirming(true);
      const res = await apiClient.confirmSchedule({
        assignments: solveResult.assignments,
        reason: `Clinician confirmed schedule proposal (${solveResult.method_label ?? "schedule"}) following capacity triage`,
      });
      setConfirmSuccess(res.message);
      setSolveResult(null);
      await loadContinuityData();
    } catch (err) {
      console.error("Failed to confirm schedule:", err);
      setStatusMessage("Failed to confirm schedule.");
    } finally {
      setIsConfirming(false);
    }
  };

  const operationalCount = machines.filter((m) => m.status === "operational").length;
  const totalDelayDays = courses.reduce((acc, c) => acc + (c.current_delay_days || 0), 0);
  const meanDelay = courses.length > 0 ? (totalDelayDays / courses.length).toFixed(1) : "0";

  return (
    <div className="space-y-6">
      {/* Top Header & Metrics Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-indigo-100 text-indigo-800 border border-indigo-200">
                Module M7
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-900 border border-amber-300 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3 text-amber-700" />
                Simulation-only evidence · no real-data validation
              </span>
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Clinician confirms every change
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">
              Treatment Continuity & Radiotherapy Triage
            </h1>
            <p className="text-sm text-slate-600 mt-1 max-w-3xl">
              Linear accelerator (LINAC) capacity triage. By default Vigil proposes an explainable urgency ranking:
              courses already in progress first, then clinician-flagged urgent courses, then clinical tier, then
              waiting time. Every proposal shows why each patient is where they are; nothing is applied until a
              clinician confirms it.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadContinuityData}
              disabled={isLoading}
              className="flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Global KPIs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6 pt-6 border-t border-slate-100">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-medium text-slate-500 uppercase">Operational LINACs</span>
            <div className="text-xl font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-indigo-600" />
              <span>{operationalCount} / {machines.length}</span>
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-medium text-slate-500 uppercase">Active RT Courses</span>
            <div className="text-xl font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <Activity className="w-5 h-5 text-blue-600" />
              <span>{courses.length}</span>
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-medium text-slate-500 uppercase">Mean Wait / Delay</span>
            <div className="text-xl font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-600" />
              <span>{meanDelay} days</span>
            </div>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-xs font-medium text-slate-500 uppercase">Fairness Bound (Max Disparity)</span>
            <div className="text-xl font-bold text-slate-900 mt-0.5 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <span>&le; {fairnessBound} days</span>
            </div>
          </div>
        </div>

        {/* Status Alerts */}
        {confirmSuccess && (
          <div className="mt-4 p-3 bg-emerald-50 border border-emerald-300 text-emerald-900 rounded-lg text-sm flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{confirmSuccess}</span>
          </div>
        )}
        {statusMessage && !confirmSuccess && (
          <div className="mt-4 p-3 bg-slate-100 border border-slate-300 text-slate-800 rounded-lg text-sm flex items-center justify-between">
            <span>{statusMessage}</span>
            <button onClick={() => setStatusMessage(null)} className="text-xs text-slate-500 hover:text-slate-800 underline">
              Dismiss
            </button>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 space-x-2" role="tablist">
        <button
          role="tab"
          aria-selected={activeTab === "scheduler"}
          onClick={() => setActiveTab("scheduler")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "scheduler"
              ? "border-indigo-600 text-indigo-700 bg-white"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Zap className="w-4 h-4" />
          Schedule Proposal
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "courses"}
          onClick={() => setActiveTab("courses")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "courses"
              ? "border-indigo-600 text-indigo-700 bg-white"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Layers className="w-4 h-4" />
          Treatment Courses ({courses.length})
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "machines"}
          onClick={() => setActiveTab("machines")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "machines"
              ? "border-indigo-600 text-indigo-700 bg-white"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Cpu className="w-4 h-4" />
          LINAC Machines ({machines.length})
        </button>
        <button
          role="tab"
          aria-selected={activeTab === "ledger"}
          onClick={() => setActiveTab("ledger")}
          className={`px-4 py-2 text-sm font-semibold border-b-2 transition-colors flex items-center gap-2 ${
            activeTab === "ledger"
              ? "border-indigo-600 text-indigo-700 bg-white"
              : "border-transparent text-slate-600 hover:text-slate-900"
          }`}
        >
          <Calendar className="w-4 h-4" />
          Delay Ledger ({ledger.length})
        </button>
      </div>

      {/* Tab 1: Schedule proposal (urgency ranking default; CP-SAT research opt-in) */}
      {activeTab === "scheduler" && (
        <div className="space-y-6">
          {/* Controls Bar */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex flex-wrap items-center gap-4 text-sm">
              <div>
                <label htmlFor="method-select" className="block text-xs font-semibold text-slate-700 mb-1">
                  Method
                </label>
                <select
                  id="method-select"
                  value={method}
                  onChange={(e) => setMethod(e.target.value as "urgency_ranking" | "cpsat_research")}
                  className="px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm"
                >
                  <option value="urgency_ranking">Explainable urgency ranking (default)</option>
                  <option value="cpsat_research">CP-SAT optimiser (research, unvalidated in simulation)</option>
                </select>
              </div>

              <div>
                <label htmlFor="horizon-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Horizon (Days)
                </label>
                <input
                  id="horizon-input"
                  type="number"
                  min={7}
                  max={60}
                  value={horizonDays}
                  onChange={(e) => setHorizonDays(Number(e.target.value))}
                  className="w-24 px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label htmlFor="fairness-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Fairness Bound (Days, CP-SAT only)
                </label>
                <input
                  id="fairness-input"
                  type="number"
                  min={1}
                  max={15}
                  step={0.5}
                  value={fairnessBound}
                  onChange={(e) => setFairnessBound(Number(e.target.value))}
                  className="w-28 px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm"
                />
              </div>

              <div>
                <label htmlFor="maxwait-input" className="block text-xs font-semibold text-slate-700 mb-1">
                  Starvation Ceiling W_max (advisory warning for urgency ranking)
                </label>
                <input
                  id="maxwait-input"
                  type="number"
                  min={10}
                  max={60}
                  value={maxWaitDays}
                  onChange={(e) => setMaxWaitDays(Number(e.target.value))}
                  className="w-28 px-2.5 py-1.5 border border-slate-300 rounded-lg text-sm"
                />
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant="primary"
                onClick={handleSolveSchedule}
                disabled={isSolving}
                className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-4 py-2 rounded-lg"
              >
                <Cpu className={`w-4 h-4 ${isSolving ? "animate-spin" : ""}`} />
                {isSolving ? "Proposing schedule..." : "Propose Schedule"}
              </Button>
            </div>
          </div>

          {/* Solution Proposed Banner */}
          {solveResult && (
            <div className="bg-indigo-50 border border-indigo-200 rounded-xl p-5 shadow-sm space-y-4">
              <div className="p-3 bg-amber-50 border border-amber-300 rounded-lg text-xs text-amber-900 font-medium flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-700 flex-shrink-0" />
                <span>
                  <strong>Clinical Notice:</strong> {solveResult.method_label ?? "Schedule proposal"} — <em>{solveResult.validation_status ?? "unvalidated in simulation"}</em>. Mandatory human oncologist review and sign-off is required before clinical execution.
                </span>
              </div>
              {(solveResult.warnings ?? []).length > 0 && (
                <ul
                  role="alert"
                  className="p-3 bg-red-50 border border-red-300 rounded-lg text-xs text-red-900 font-medium space-y-1 list-disc list-inside"
                >
                  {(solveResult.warnings ?? []).map((w) => (
                    <li key={w}>{w}</li>
                  ))}
                </ul>
              )}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded bg-indigo-200 text-indigo-900 font-bold text-xs">
                      Status: {solveResult.status}
                    </span>
                    <span className="text-xs text-indigo-800">
                      Solve Time: {solveResult.solver_time_seconds}s
                    </span>
                    <span className="text-xs text-indigo-800 font-medium">
                      Subgroup Disparity: {solveResult.fairness_disparity} days{" "}
                      {solveResult.fairness_bound_enforced
                        ? `(bound ${fairnessBound}d enforced by this method)`
                        : "(realised value; this method does not enforce a bound)"}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-indigo-950 mt-1">
                    Proposed schedule — {solveResult.method_label ?? ""} ({solveResult.assignments.length} patients allocated)
                  </h3>
                </div>

                <Button
                  variant="primary"
                  onClick={handleConfirmSchedule}
                  disabled={isConfirming}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-4 py-2 rounded-lg shadow-sm flex items-center gap-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  {isConfirming ? "Persisting..." : "Confirm & Commit Schedule"}
                </Button>
              </div>

              {/* Proposed Assignments Table */}
              <div className="overflow-x-auto border border-indigo-200 rounded-lg bg-white">
                <table className="w-full text-left text-sm" aria-label="Proposed Schedule Table">
                  <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Patient ID</th>
                      <th className="px-4 py-2.5">Context</th>
                      <th className="px-4 py-2.5">Machine</th>
                      <th className="px-4 py-2.5">Scheduled Date</th>
                      <th className="px-4 py-2.5">Delay (Days)</th>
                      <th className="px-4 py-2.5">Marginal Harm</th>
                      <th className="px-4 py-2.5">Move Justification</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {solveResult.assignments.map((a) => (
                      <tr key={a.patient_id} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 font-bold text-slate-900">{a.patient_id}</td>
                        <td className="px-4 py-2.5">
                          <span className="px-2 py-0.5 rounded text-xs bg-slate-100 text-slate-800 font-medium">
                            {a.context.replace("_", " ")}
                          </span>
                        </td>
                        <td className="px-4 py-2.5 text-slate-700 font-medium">{a.machine_id}</td>
                        <td className="px-4 py-2.5 text-slate-800">
                          {new Date(a.scheduled_date).toLocaleDateString("en-NG", {
                            month: "short",
                            day: "numeric",
                          })} (Day {a.start_day})
                        </td>
                        <td className="px-4 py-2.5 font-semibold text-amber-700">{a.delay_days}d</td>
                        <td className="px-4 py-2.5 font-mono text-xs text-rose-700">
                          {(a.marginal_harm * 100).toFixed(2)}%
                        </td>
                        <td className="px-4 py-2.5 text-xs text-slate-600 max-w-xs">{a.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Machine Status Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {machines.map((m) => (
              <div
                key={m.id}
                className={`p-5 rounded-xl border transition-all ${
                  m.status === "operational"
                    ? "bg-white border-slate-200 shadow-sm"
                    : "bg-rose-50/50 border-rose-200 shadow-sm"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-bold text-slate-900 text-base">{m.machine_name}</h3>
                    <p className="text-xs text-slate-700 mt-0.5">ID: {m.id} &bull; Capacity: {m.daily_slot_capacity} slots/day</p>
                  </div>
                  <span
                    className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                      m.status === "operational"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-rose-100 text-rose-800 border border-rose-300"
                    }`}
                  >
                    {m.status}
                  </span>
                </div>

                {m.status !== "operational" && (
                  <div className="mt-3 p-2.5 bg-rose-100/70 border border-rose-200 rounded-lg text-xs text-rose-900 flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0" />
                    <span>
                      Machine down. Expected return:{" "}
                      {m.expected_return_at
                        ? new Date(m.expected_return_at).toLocaleDateString("en-NG")
                        : "Pending technician assessment"}
                    </span>
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between">
                  <span className="text-xs text-slate-700">
                    Slot Utilization: {m.daily_slot_capacity} fractions/day
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleToggleMachineStatus(m)}
                    className="text-xs font-medium"
                  >
                    {m.status === "operational" ? "Simulate Breakdown" : "Restore Operation"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab 2: Treatment Courses Table */}
      {activeTab === "courses" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm">Active Radiotherapy Courses</h3>
            <span className="text-xs text-slate-500">
              Evaluated via piecewise E8 Continuity Harm Model
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" aria-label="Radiotherapy Courses Table">
              <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Clinical Indication</th>
                  <th className="px-4 py-3">Fractions</th>
                  <th className="px-4 py-3">Prescribed Start</th>
                  <th className="px-4 py-3">Scheduled Start</th>
                  <th className="px-4 py-3">Delay</th>
                  <th className="px-4 py-3">Excess Harm (&Delta; Risk)</th>
                  <th className="px-4 py-3">Urgency Tier</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {courses.map((c) => (
                  <tr key={c.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-bold text-slate-900">{c.patient_id}</td>
                    <td className="px-4 py-3">
                      <span className="px-2 py-0.5 rounded text-xs bg-indigo-50 text-indigo-800 font-medium">
                        {c.clinical_context.replace("_", " ")}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {c.fractions_delivered} / {c.total_fractions}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {new Date(c.prescribed_start_date).toLocaleDateString("en-NG")}
                    </td>
                    <td className="px-4 py-3 text-slate-900 font-medium">
                      {c.scheduled_start_date
                        ? new Date(c.scheduled_start_date).toLocaleDateString("en-NG")
                        : "Unscheduled"}
                    </td>
                    <td className="px-4 py-3 font-semibold text-amber-700">
                      {c.current_delay_days ?? 0} days
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-rose-700 font-semibold">
                      {(((c.expected_excess_harm ?? 0) * 100)).toFixed(2)}%
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                          c.urgency_tier === "urgent" || c.urgency_tier === "emergency"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-slate-100 text-slate-700"
                        }`}
                      >
                        {c.urgency_tier}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab 3: LINAC Machines View */}
      {activeTab === "machines" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {machines.map((m) => (
            <div key={m.id} className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-4">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-bold text-slate-900">{m.machine_name}</h3>
                  <p className="text-xs text-slate-500">Machine UUID: {m.id}</p>
                </div>
                <span
                  className={`px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                    m.status === "operational"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : "bg-rose-100 text-rose-800 border border-rose-300"
                  }`}
                >
                  {m.status}
                </span>
              </div>

              <div className="space-y-2 text-sm text-slate-700 border-t border-slate-100 pt-3">
                <div className="flex justify-between">
                  <span className="text-slate-500">Daily Slot Capacity:</span>
                  <span className="font-semibold text-slate-900">{m.daily_slot_capacity} fractions / day</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Maintenance Status:</span>
                  <span className="font-semibold text-slate-900">
                    {m.status === "operational" ? "Calibrated & Active" : "Unscheduled Repair"}
                  </span>
                </div>
                {m.downtime_started_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Downtime Started:</span>
                    <span className="font-semibold text-rose-700">
                      {new Date(m.downtime_started_at).toLocaleDateString("en-NG")}
                    </span>
                  </div>
                )}
                {m.expected_return_at && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">Expected Return:</span>
                    <span className="font-semibold text-indigo-700">
                      {new Date(m.expected_return_at).toLocaleDateString("en-NG")}
                    </span>
                  </div>
                )}
              </div>

              <div className="pt-2">
                <Button
                  variant="outline"
                  onClick={() => handleToggleMachineStatus(m)}
                  className="w-full text-xs font-semibold py-2"
                >
                  {m.status === "operational" ? "Flag Machine Breakdown (Down)" : "Mark Machine Operational"}
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab 4: Delay Ledger */}
      {activeTab === "ledger" && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm">Audited Delay Ledger</h3>
            <span className="text-xs text-slate-500">
              Immutable log of treatment shifts, marginal harms, and clinician confirmations (M7)
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm" aria-label="Delay Ledger Table">
              <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Patient</th>
                  <th className="px-4 py-3">Total Delay</th>
                  <th className="px-4 py-3">Reason</th>
                  <th className="px-4 py-3">Marginal Harm</th>
                  <th className="px-4 py-3">Moved Dates</th>
                  <th className="px-4 py-3">Recorded By</th>
                  <th className="px-4 py-3">Timestamp</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {ledger.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-sm text-slate-500">
                      No delay ledger records yet. Confirm a CP-SAT schedule to create audited entries.
                    </td>
                  </tr>
                ) : (
                  ledger.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3 font-bold text-slate-900">{entry.patient_id}</td>
                      <td className="px-4 py-3 font-semibold text-amber-700">{entry.delay_days} days</td>
                      <td className="px-4 py-3 text-slate-700 text-xs max-w-sm">{entry.reason}</td>
                      <td className="px-4 py-3 font-mono text-xs text-rose-700">
                        {entry.marginal_harm != null ? `${((entry.marginal_harm ?? 0) * 100).toFixed(2)}%` : "N/A"}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {entry.moved_from_date
                          ? new Date(entry.moved_from_date).toLocaleDateString("en-NG")
                          : "Prescribed"}{" "}
                        &rarr; {new Date(entry.moved_to_date).toLocaleDateString("en-NG")}
                      </td>
                      <td className="px-4 py-3 font-medium text-slate-800 text-xs">{entry.recorded_by}</td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {new Date(entry.created_at).toLocaleDateString("en-NG", {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
