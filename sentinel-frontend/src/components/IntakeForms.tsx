"use client";

import React, { useState } from "react";
import { UserPlus, FileSpreadsheet, TestTube2, Check, ArrowRight, Activity } from "lucide-react";
import { createPatient, submitBaseline, submitLabResult } from "@/lib/api";

interface IntakeFormsProps {
  patientList: { id: string; age: number }[];
  selectedPatientId: string | null;
  onSuccess: (newPatientId?: string) => void;
}

export const IntakeForms: React.FC<IntakeFormsProps> = ({
  patientList,
  selectedPatientId,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<"patient" | "baseline" | "labs">("labs");

  // Patient Enrollment State
  const [age, setAge] = useState<number>(55);
  const [patientLoading, setPatientLoading] = useState(false);

  // Baseline Profile State
  const [baselinePatientId, setBaselinePatientId] = useState<string>(selectedPatientId || "");
  const [stage, setStage] = useState<number>(2);
  const [er, setEr] = useState<boolean>(true);
  const [pr, setPr] = useState<boolean>(true);
  const [her2, setHer2] = useState<boolean>(false);
  const [hypertension, setHypertension] = useState<boolean>(false);
  const [renal, setRenal] = useState<boolean>(false);
  const [baselineLoading, setBaselineLoading] = useState(false);
  const [baselineFeedback, setBaselineFeedback] = useState<string | null>(null);

  // Lab Result State
  const [labPatientId, setLabPatientId] = useState<string>(selectedPatientId || "");
  const [alt, setAlt] = useState<number>(22.0);
  const [ast, setAst] = useState<number>(20.0);
  const [creatinine, setCreatinine] = useState<number>(0.85);
  const [ca153, setCa153] = useState<number>(18.0);
  const [wbc, setWbc] = useState<number>(6.5);
  const [labLoading, setLabLoading] = useState(false);
  const [labFeedback, setLabFeedback] = useState<string | null>(null);

  // Synchronize selected patient from parent
  React.useEffect(() => {
    if (selectedPatientId) {
      setBaselinePatientId(selectedPatientId);
      setLabPatientId(selectedPatientId);
    } else if (patientList.length > 0) {
      setBaselinePatientId(patientList[0].id);
      setLabPatientId(patientList[0].id);
    }
  }, [selectedPatientId, patientList]);

  // Handle Patient Enrollment
  const handleEnrollPatient = async (e: React.FormEvent) => {
    e.preventDefault();
    setPatientLoading(true);
    try {
      const newP = await createPatient({ age, status: "active" });
      onSuccess(newP.id);
      setActiveTab("baseline");
    } catch (err: any) {
      alert("Error enrolling patient: " + err.message);
    } finally {
      setPatientLoading(false);
    }
  };

  // Handle Baseline Profile Submission
  const handleBaselineSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!baselinePatientId) return alert("Please select a patient.");
    setBaselineLoading(true);
    setBaselineFeedback(null);
    try {
      const res = await submitBaseline(baselinePatientId, {
        tumor_stage: stage,
        er_status: er,
        pr_status: pr,
        her2_status: her2,
        has_hypertension: hypertension,
        renal_history: renal,
      });
      const vec = res.target_organ_susceptibility_vector;
      setBaselineFeedback(
        `Baseline processed by Model A (XGBoost). Organ Susceptibility -> Bone: ${(vec.bone * 100).toFixed(0)}%, Liver: ${(vec.liver * 100).toFixed(0)}%, Lung: ${(vec.lung * 100).toFixed(0)}%, Brain: ${(vec.brain * 100).toFixed(0)}%.`
      );
      onSuccess(baselinePatientId);
    } catch (err: any) {
      alert("Error submitting baseline: " + err.message);
    } finally {
      setBaselineLoading(false);
    }
  };

  // Handle Lab Result Submission
  const handleLabSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!labPatientId) return alert("Please select a patient.");
    setLabLoading(true);
    setLabFeedback(null);
    try {
      const res = await submitLabResult(labPatientId, {
        date_drawn: new Date().toISOString(),
        alt_level: Number(alt),
        ast_level: Number(ast),
        creatinine: Number(creatinine),
        ca_15_3: Number(ca153),
        wbc_count: Number(wbc),
      });
      const riskPct = (res.calculated_metastasis_risk * 100).toFixed(1);
      setLabFeedback(
        `Lab evaluated by Model B (PyTorch LSTM). Calculated Risk: ${riskPct}%. Triage Flag: ${res.triage_flag ? "ALERT (≥75%)" : "STABLE"}.`
      );
      onSuccess(labPatientId);
    } catch (err: any) {
      alert("Error submitting lab: " + err.message);
    } finally {
      setLabLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      {/* Header and Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div>
          <h2 className="text-base font-bold text-white tracking-wide flex items-center gap-2">
            <FileSpreadsheet className="w-5 h-5 text-cyan-400" />
            View 2: Clinical Intake Side-Panels
          </h2>
          <p className="text-xs text-slate-400">
            Enroll patients, submit baseline tumor pathology, or enter new longitudinal lab draws.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs font-medium">
          <button
            onClick={() => setActiveTab("labs")}
            className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
              activeTab === "labs" ? "bg-cyan-600 text-white font-semibold" : "text-slate-400 hover:text-white"
            }`}
          >
            <TestTube2 className="w-3.5 h-3.5" /> Lab Results
          </button>
          <button
            onClick={() => setActiveTab("baseline")}
            className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
              activeTab === "baseline" ? "bg-cyan-600 text-white font-semibold" : "text-slate-400 hover:text-white"
            }`}
          >
            <Activity className="w-3.5 h-3.5" /> Baseline Profile
          </button>
          <button
            onClick={() => setActiveTab("patient")}
            className={`px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
              activeTab === "patient" ? "bg-cyan-600 text-white font-semibold" : "text-slate-400 hover:text-white"
            }`}
          >
            <UserPlus className="w-3.5 h-3.5" /> Enroll Patient
          </button>
        </div>
      </div>

      {/* Tab 1: New Patient Form */}
      {activeTab === "patient" && (
        <form onSubmit={handleEnrollPatient} className="space-y-4 max-w-lg">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Patient Age (Years)</label>
            <input
              type="number"
              min="20"
              max="100"
              required
              value={age}
              onChange={(e) => setAge(parseInt(e.target.value))}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={patientLoading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-2"
          >
            {patientLoading ? "Enrolling..." : "Enroll Patient & Proceed to Baseline"}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>
      )}

      {/* Tab 2: Baseline Pathology Form */}
      {activeTab === "baseline" && (
        <form onSubmit={handleBaselineSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Select Patient</label>
              <select
                value={baselinePatientId}
                onChange={(e) => setBaselinePatientId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              >
                {patientList.map((p) => (
                  <option key={p.id} value={p.id}>
                    Patient {p.id.slice(0, 8)}... ({p.age}yo)
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-300">Tumor Stage (I - IV)</label>
              <select
                value={stage}
                onChange={(e) => setStage(parseInt(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              >
                <option value={1}>Stage I (Localized)</option>
                <option value={2}>Stage II (Invasive / Regional Nodes)</option>
                <option value={3}>Stage III (Locally Advanced)</option>
                <option value={4}>Stage IV (Overt Metastatic Dissemination)</option>
              </select>
            </div>
          </div>

          {/* Molecular Receptors Switches */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-300">Primary Receptor Status</span>
            <div className="grid grid-cols-3 gap-3">
              <button
                type="button"
                onClick={() => setEr(!er)}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  er ? "bg-cyan-950 border-cyan-500 text-cyan-300" : "bg-slate-950 border-slate-800 text-slate-500"
                }`}
              >
                ER: {er ? "POSITIVE (+)" : "NEGATIVE (-)"}
              </button>
              <button
                type="button"
                onClick={() => setPr(!pr)}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  pr ? "bg-cyan-950 border-cyan-500 text-cyan-300" : "bg-slate-950 border-slate-800 text-slate-500"
                }`}
              >
                PR: {pr ? "POSITIVE (+)" : "NEGATIVE (-)"}
              </button>
              <button
                type="button"
                onClick={() => setHer2(!her2)}
                className={`py-2 px-3 rounded-lg border text-xs font-bold transition-all ${
                  her2 ? "bg-rose-950 border-rose-500 text-rose-300" : "bg-slate-950 border-slate-800 text-slate-500"
                }`}
              >
                HER2: {her2 ? "POSITIVE (+)" : "NEGATIVE (-)"}
              </button>
            </div>
          </div>

          {/* Comorbidities */}
          <div className="flex gap-6 text-xs text-slate-300">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={hypertension}
                onChange={(e) => setHypertension(e.target.checked)}
                className="rounded border-slate-800 bg-slate-950 text-cyan-500"
              />
              History of Hypertension
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={renal}
                onChange={(e) => setRenal(e.target.checked)}
                className="rounded border-slate-800 bg-slate-950 text-cyan-500"
              />
              Renal Disease History
            </label>
          </div>

          <button
            type="submit"
            disabled={baselineLoading}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-2"
          >
            {baselineLoading ? "Processing Model A..." : "Submit Pathology & Run Model A Profiler"}
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          {baselineFeedback && (
            <div className="p-3 bg-cyan-950/50 border border-cyan-800 rounded-lg text-xs text-cyan-300">
              {baselineFeedback}
            </div>
          )}
        </form>
      )}

      {/* Tab 3: Lab Result Entry Form */}
      {activeTab === "labs" && (
        <form onSubmit={handleLabSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Select Patient</label>
            <select
              value={labPatientId}
              onChange={(e) => setLabPatientId(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
            >
              {patientList.map((p) => (
                <option key={p.id} value={p.id}>
                  Patient {p.id.slice(0, 8)}... ({p.age}yo)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300 flex justify-between">
                <span>ALT Level</span>
                <span className="text-[10px] text-slate-500">10-35 U/L</span>
              </label>
              <input
                type="number"
                step="0.1"
                required
                value={alt}
                onChange={(e) => setAlt(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300 flex justify-between">
                <span>AST Level</span>
                <span className="text-[10px] text-slate-500">10-35 U/L</span>
              </label>
              <input
                type="number"
                step="0.1"
                required
                value={ast}
                onChange={(e) => setAst(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300 flex justify-between">
                <span>Creatinine</span>
                <span className="text-[10px] text-slate-500">0.6-1.1 mg/dL</span>
              </label>
              <input
                type="number"
                step="0.01"
                required
                value={creatinine}
                onChange={(e) => setCreatinine(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-amber-400 flex justify-between">
                <span>CA 15-3</span>
                <span className="text-[10px] text-slate-500">&lt;30 U/mL</span>
              </label>
              <input
                type="number"
                step="0.1"
                required
                value={ca153}
                onChange={(e) => setCa153(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-amber-800/80 rounded-lg px-2.5 py-1.5 text-xs text-amber-300 font-mono focus:outline-none focus:border-amber-500"
              />
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-slate-300 flex justify-between">
                <span>WBC Count</span>
                <span className="text-[10px] text-slate-500">4.5-10.0 x10^9</span>
              </label>
              <input
                type="number"
                step="0.1"
                required
                value={wbc}
                onChange={(e) => setWbc(parseFloat(e.target.value))}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="submit"
              disabled={labLoading}
              className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow transition-all flex items-center gap-2"
            >
              {labLoading ? "Running Model B LSTM..." : "Record Lab Draw & Trigger Anomaly Detection"}
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            {/* Quick Demo Anomaly Presets */}
            <button
              type="button"
              onClick={() => {
                setAlt(98.0);
                setAst(86.0);
                setCa153(68.0);
                setWbc(10.5);
              }}
              className="px-3 py-2 bg-rose-950/60 hover:bg-rose-900 border border-rose-800 text-rose-300 text-xs font-medium rounded-lg transition-colors"
            >
              ⚡ Load Recurrence Anomaly Preset (ALT 98, CA 15-3 68)
            </button>
            <button
              type="button"
              onClick={() => {
                setAlt(22.0);
                setAst(20.0);
                setCreatinine(0.85);
                setCa153(16.5);
                setWbc(6.2);
              }}
              className="px-3 py-2 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-medium rounded-lg transition-colors"
            >
              ↺ Reset to Normal Range
            </button>
          </div>

          {labFeedback && (
            <div className="p-3 bg-slate-950 border border-slate-700 rounded-lg text-xs font-mono text-cyan-300">
              {labFeedback}
            </div>
          )}
        </form>
      )}
    </div>
  );
};
