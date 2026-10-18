"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useTranslation, Button } from "@vigil/ui";
import { qualityApiClient } from "@/lib/api";
import { QualityAuditResponse, StratumAuditMetricResponse } from "@/lib/types";
import {
  ShieldAlert,
  FileCheck,
  AlertTriangle,
  Lock,
  RefreshCw,
  BarChart3,
  Calendar,
  Layers,
  Info,
  CheckCircle2,
} from "lucide-react";

export default function QualityAuditPage() {
  const { t } = useTranslation();

  // State
  const [auditData, setAuditData] = useState<QualityAuditResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isAuditing, setIsAuditing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form Parameters
  const [lookbackDays, setLookbackDays] = useState<number>(365);
  const [nBootstrap, setNBootstrap] = useState<number>(500);

  // Active breakdown tab
  const [activeTab, setActiveTab] = useState<"subgroup" | "subtype" | "stage">("subgroup");

  // Load latest audit on mount
  const loadInitialAudit = useCallback(async () => {
    try {
      setIsLoading(true);
      setErrorMessage(null);
      const data = await qualityApiClient.getLatestQualityAudit();
      setAuditData(data);
    } catch (err: unknown) {
      console.error("Failed to load initial quality audit:", err);
      // Fallback: run initial audit if none cached
      try {
        const fresh = await qualityApiClient.runQualityAudit({
          lookback_days: 365,
          n_bootstrap: 200,
          include_synthetic_benchmark: true,
        });
        setAuditData(fresh);
      } catch (innerErr: unknown) {
        setErrorMessage(
          innerErr instanceof Error ? innerErr.message : "Unable to load quality audit data."
        );
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialAudit();
  }, [loadInitialAudit]);

  // Handle running fresh audit
  const handleRunAudit = async () => {
    try {
      setIsAuditing(true);
      setErrorMessage(null);
      const res = await qualityApiClient.runQualityAudit({
        lookback_days: lookbackDays,
        n_bootstrap: nBootstrap,
        include_synthetic_benchmark: true,
      });
      setAuditData(res);
    } catch (err: unknown) {
      setErrorMessage(
        err instanceof Error ? err.message : "Failed to execute quality audit."
      );
    } finally {
      setIsAuditing(false);
    }
  };

  const renderBreakdownTable = (
    title: string,
    breakdown: Record<string, StratumAuditMetricResponse> | undefined
  ) => {
    if (!breakdown || Object.keys(breakdown).length === 0) {
      return (
        <div className="p-8 text-center text-slate-500 italic">
          No breakdown strata available for this view.
        </div>
      );
    }

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm" role="table" aria-label={title}>
          <thead className="bg-slate-100/75 border-b border-slate-200 text-xs font-semibold uppercase text-slate-600">
            <tr>
              <th scope="col" className="px-4 py-3">Stratum</th>
              <th scope="col" className="px-4 py-3 text-right">Total Signals</th>
              <th scope="col" className="px-4 py-3 text-right">Action Not Recorded</th>
              <th scope="col" className="px-4 py-3 text-right">Unaddressed Rate</th>
              <th scope="col" className="px-4 py-3 text-center">Privacy Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {Object.entries(breakdown).map(([stratumName, metric]) => {
              const formattedName = stratumName
                .replace(/_/g, " ")
                .replace(/\b\w/g, (c) => c.toUpperCase());

              return (
                <tr
                  key={stratumName}
                  className={`hover:bg-slate-50/75 transition-colors ${
                    metric.is_suppressed ? "bg-amber-50/40" : ""
                  }`}
                >
                  <td className="px-4 py-3.5 font-medium text-slate-900 flex items-center gap-2">
                    {formattedName}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono">
                    {metric.is_suppressed ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                        &lt;5
                      </span>
                    ) : (
                      metric.total_signals
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono">
                    {metric.is_suppressed ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-300">
                        &lt;5
                      </span>
                    ) : (
                      metric.action_not_recorded_count
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-right font-mono">
                    {metric.is_suppressed || typeof metric.action_not_recorded_rate !== "number" ? (
                      <span className="text-slate-600 font-medium italic">Suppressed</span>
                    ) : (
                      <span className="font-semibold text-slate-800">
                        {(metric.action_not_recorded_rate * 100).toFixed(1)}%
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3.5 text-center">
                    {metric.is_suppressed ? (
                      <span
                        className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-900 border border-amber-300"
                        title="Cell count satisfies 1 <= n < 5; suppressed to prevent deductive patient re-identification."
                      >
                        <Lock className="w-3 h-3 text-amber-700" aria-hidden="true" />
                        k &ge; 5 Suppressed
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-800 border border-emerald-300">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" aria-hidden="true" />
                        Standard Cell (n &ge; 5)
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Title & Governance Badge Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-purple-100 text-purple-700 rounded-lg">
              <ShieldAlert className="w-6 h-6" aria-hidden="true" />
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900">
              Surveillance Quality & Missed-Signal Audit (M10)
            </h2>
          </div>
          <p className="text-sm text-slate-500 max-w-3xl">
            Retrospective clinical governance identifying surveillance drift, unaddressed biomarker
            surges, and diagnostic lead-time bottlenecks under strictly neutral, non-punitive
            recording standards.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {auditData && (
            <div className="text-right">
              <div className="text-xs text-slate-600 font-medium font-mono">Audit ID</div>
              <div className="text-xs font-bold font-mono text-purple-800 bg-purple-50 px-2.5 py-1 rounded border border-purple-200">
                {auditData.audit_id}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mandatory Governance Notice */}
      <div className="bg-purple-50 border border-purple-200 rounded-xl p-4.5 text-xs text-purple-950 flex items-start gap-3 shadow-sm">
        <Info className="w-5 h-5 text-purple-700 shrink-0 mt-0.5" aria-hidden="true" />
        <div className="space-y-1">
          <span className="font-bold text-sm block text-purple-900">
            ADR 0016 Institutional Privacy & Descriptive Register Policy
          </span>
          <p className="text-purple-900 leading-relaxed">
            All findings are reported in a factual descriptive register (&quot;signal present,
            action not recorded&quot;). No individual clinician names, license numbers, or punitive
            characterizations are recorded. Intersectional cells with 1 &le; n &lt; 5 are
            automatically masked as &quot;&lt;5&quot; to prevent deductive patient re-identification
            under the Nigeria Data Protection Act (NDPA 2023).
          </p>
        </div>
      </div>

      {/* Audit Parameter Controls */}
      <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="lookback-select" className="text-xs font-semibold text-slate-700">
              Surveillance Lookback:
            </label>
            <select
              id="lookback-select"
              value={lookbackDays}
              onChange={(e) => setLookbackDays(Number(e.target.value))}
              className="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value={90}>90 Days (Quarterly)</option>
              <option value={180}>180 Days (Semi-Annual)</option>
              <option value={365}>365 Days (Annual)</option>
              <option value={730}>730 Days (2-Year)</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="bootstrap-select" className="text-xs font-semibold text-slate-700">
              Bootstrap Resamples:
            </label>
            <select
              id="bootstrap-select"
              value={nBootstrap}
              onChange={(e) => setNBootstrap(Number(e.target.value))}
              className="bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1 text-xs font-medium text-slate-800 focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value={200}>200 Resamples (Fast)</option>
              <option value={500}>500 Resamples (Standard)</option>
              <option value={1000}>1,000 Resamples (High Precision)</option>
            </select>
          </div>
        </div>

        <button
          onClick={handleRunAudit}
          disabled={isAuditing}
          className="inline-flex items-center gap-2 px-4 py-2 bg-purple-700 hover:bg-purple-800 text-white rounded-lg text-xs font-bold shadow-sm transition-all disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isAuditing ? "animate-spin" : ""}`} />
          {isAuditing ? "Auditing Trajectories..." : "Run Retrospective Audit"}
        </button>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="bg-rose-50 border border-rose-300 text-rose-900 p-4 rounded-xl text-xs flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-rose-700 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Summary KPI Cards */}
      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="bg-slate-100 h-28 rounded-xl border border-slate-200" />
          ))}
        </div>
      ) : auditData ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Card 1: Patients Audited */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Total Audited Cohort
            </span>
            <div className="text-3xl font-extrabold text-slate-900">
              {auditData.total_patients_audited.toLocaleString()}
            </div>
            <p className="text-xs text-slate-600 font-medium">
              Longitudinal surveillance trajectories
            </p>
          </div>

          {/* Card 2: Surveillance Signals */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Signals Meeting Criteria
            </span>
            <div className="text-3xl font-extrabold text-purple-700">
              {auditData.total_signals_detected}
            </div>
            <p className="text-xs text-slate-600 font-medium">
              Review or urgent threshold triggers
            </p>
          </div>

          {/* Card 3: Timely Action Recorded */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Timely Action Recorded
            </span>
            <div className="text-3xl font-extrabold text-emerald-700">
              {auditData.total_action_recorded}
            </div>
            <p className="text-xs text-emerald-800 font-medium">
              Investigated within 30-day grace window
            </p>
          </div>

          {/* Card 4: Action Not Recorded */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
              Action Not Recorded
            </span>
            <div className="text-3xl font-extrabold text-amber-700 flex items-baseline gap-2">
              <span>{auditData.total_action_not_recorded}</span>
              <span className="text-sm font-semibold text-amber-900">
                ({(auditData.overall_action_not_recorded_rate * 100).toFixed(1)}%)
              </span>
            </div>
            <p className="text-xs text-slate-700 font-medium">
              95% CI: [{(auditData.overall_bootstrap_ci_95[0] * 100).toFixed(1)}%,{" "}
              {(auditData.overall_bootstrap_ci_95[1] * 100).toFixed(1)}%]
            </p>
          </div>
        </div>
      ) : null}

      {/* Verified Narrative Card */}
      {auditData && (
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
              <FileCheck className="w-4 h-4 text-purple-700" />
              Verified Neutral Narrative
            </span>
            <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
              Descriptive Register Verified
            </span>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed font-sans bg-slate-50 p-4 rounded-lg border border-slate-200">
            {auditData.narrative_summary}
          </p>
        </div>
      )}

      {/* Stratified Breakdown Tables */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {/* Table Tabs */}
        <div className="flex border-b border-slate-200 bg-slate-50/50 px-4 pt-3 gap-2">
          <button
            onClick={() => setActiveTab("subgroup")}
            className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-colors border-t border-x cursor-pointer ${
              activeTab === "subgroup"
                ? "bg-white text-purple-900 border-slate-200 -mb-px"
                : "text-slate-600 hover:text-slate-900 border-transparent"
            }`}
          >
            Subgroup Breakdown
          </button>
          <button
            onClick={() => setActiveTab("subtype")}
            className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-colors border-t border-x cursor-pointer ${
              activeTab === "subtype"
                ? "bg-white text-purple-900 border-slate-200 -mb-px"
                : "text-slate-600 hover:text-slate-900 border-transparent"
            }`}
          >
            Cancer Subtype
          </button>
          <button
            onClick={() => setActiveTab("stage")}
            className={`px-4 py-2.5 text-xs font-bold rounded-t-lg transition-colors border-t border-x cursor-pointer ${
              activeTab === "stage"
                ? "bg-white text-purple-900 border-slate-200 -mb-px"
                : "text-slate-600 hover:text-slate-900 border-transparent"
            }`}
          >
            Initial Stage
          </button>
        </div>

        {/* Tab Content */}
        <div className="p-4">
          {activeTab === "subgroup" &&
            renderBreakdownTable("Subgroup Breakdown", auditData?.subgroup_breakdown)}
          {activeTab === "subtype" &&
            renderBreakdownTable("Subtype Breakdown", auditData?.subtype_breakdown)}
          {activeTab === "stage" &&
            renderBreakdownTable("Stage Breakdown", auditData?.stage_breakdown)}
        </div>
      </div>
    </div>
  );
}
