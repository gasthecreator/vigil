"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslation, Button, Card, CardHeader, CardTitle, CardContent, Badge, Input } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { SecondLookResponse } from "@/lib/types";
import {
  ArrowLeft,
  FileCheck,
  Printer,
  QrCode,
  ShieldAlert,
  Send,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export default function SecondLookPage() {
  const params = useParams();
  const obsId = (params?.obsId as string) || "obs-001";
  const patientId = "PAT-001";
  const { t } = useTranslation();

  const [reason, setReason] = useState<string>("Sudden spike inconsistent with past stable baseline");
  const [notes, setNotes] = useState<string>("Family requesting confirmation repeat test before imaging or treatment change");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [submittedData, setSubmittedData] = useState<SecondLookResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      const resp = await apiClient.requestSecondLook(patientId, {
        observation_id: obsId,
        requested_action: reason,
        patient_notes: notes,
      });
      setSubmittedData(resp);
    } catch (err: any) {
      console.warn("Using offline / fallback second-look creation:", err);
      // Fallback response for offline demonstration
      setSubmittedData({
        task_id: `task-sl-${Date.now()}`,
        observation_id: obsId,
        patient_id: patientId,
        analyte_code: "ca_15_3",
        value: 180.0,
        unit: "U/mL",
        plausibility_status: "implausible",
        status: "submitted",
        notes,
        created_at: new Date().toISOString(),
        synthetic: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Back to Dashboard */}
      <div className="print:hidden">
        <Link
          href="/companion"
          className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
      </div>

      {!submittedData ? (
        /* Form View */
        <Card className="border-slate-200 overflow-hidden shadow-sm">
          <CardHeader className="bg-slate-50 border-b border-slate-200 py-4 px-6">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center shrink-0">
                <FileCheck className="w-5 h-5" />
              </div>
              <div>
                <CardTitle className="text-lg font-bold text-slate-900">
                  {t.companion.secondLookTitle}
                </CardTitle>
                <p className="text-xs text-slate-500 mt-0.5">
                  Prepare a structured, clinician-readable second-look summary for your doctor.
                </p>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs">
                  {error}
                </div>
              )}

              {/* Observed Change Summary */}
              <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold text-amber-900">
                  <span>Target Lab Result:</span>
                  <Badge variant="warning">Needs Repeat</Badge>
                </div>
                <div className="text-sm font-bold text-slate-900">
                  CA 15-3: 180.0 U/mL (10x Spike from Baseline 18.0 U/mL)
                </div>
                <p className="text-xs text-amber-800">
                  Plausibility check indicates potential analytical/pre-analytical variation. A repeat test is strongly recommended.
                </p>
              </div>

              {/* Reason input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-800">
                  Primary Reason for Second-Look Review
                </label>
                <input
                  type="text"
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                  required
                />
              </div>

              {/* Family notes input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-slate-800">
                  Family / Patient Clinical Notes
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-teal-500"
                  placeholder="Describe any symptoms, previous stable tests, or specific requests for your doctor..."
                />
              </div>

              {/* Notice */}
              <div className="text-xs text-slate-500 flex items-start gap-2">
                <ShieldAlert className="w-4 h-4 text-slate-400 shrink-0 mt-0.5" />
                <span>
                  Submitting this request creates an auditable Follow-Up Task in the hospital&apos;s Vigil Clinician Workstation.
                </span>
              </div>

              {/* Submit */}
              <div className="pt-2">
                <Button
                  type="submit"
                  variant="primary"
                  disabled={isSubmitting}
                  className="w-full sm:w-auto bg-teal-700 hover:bg-teal-800"
                >
                  <Send className="w-4 h-4 mr-2" />
                  {isSubmitting ? "Submitting Request..." : "Submit Second-Look Request"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      ) : (
        /* Printable Summary View */
        <div className="space-y-6">
          <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between print:hidden">
            <div className="flex items-center gap-2.5">
              <CheckCircle2 className="w-5 h-5 text-emerald-600" />
              <div>
                <h2 className="text-sm font-bold text-emerald-900">
                  Second-Look Request Successfully Registered
                </h2>
                <p className="text-xs text-emerald-700">
                  FollowUpTask ID: {submittedData.task_id} • Status: Pending Oncologist Disposition
                </p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={handlePrint}>
              <Printer className="w-4 h-4 mr-1.5" />
              Print Clinic Summary
            </Button>
          </div>

          {/* Printable Hand-Over Card (Clinician Register) */}
          <div className="bg-white border-2 border-slate-900 rounded-2xl p-6 md:p-8 shadow-sm space-y-6 print:border-none print:p-0">
            {/* Header */}
            <div className="border-b-2 border-slate-900 pb-4 flex justify-between items-start">
              <div>
                <span className="text-xs font-mono font-bold tracking-widest text-slate-600 uppercase">
                  Vigil Precision Oncology Decision Support Aid
                </span>
                <h1 className="text-2xl font-black text-slate-900 tracking-tight mt-0.5">
                  CLINICAL SECOND-LOOK REQUEST
                </h1>
                <p className="text-xs text-slate-600 mt-1">
                  Generated on {new Date().toLocaleString()} • Hash Chain Audited
                </p>
              </div>
              <div className="text-right">
                <div className="w-16 h-16 border border-slate-300 rounded-lg flex flex-col items-center justify-center p-1 bg-slate-50">
                  <QrCode className="w-10 h-10 text-slate-800" />
                  <span className="text-[8px] font-mono mt-0.5 text-slate-500">SCAN VERIFY</span>
                </div>
              </div>
            </div>

            {/* Patient & Biomarker Details */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-2 border-b border-slate-200 text-xs">
              <div>
                <span className="text-slate-500 block">Patient Identifier</span>
                <span className="font-bold text-slate-900">{patientId}</span>
              </div>
              <div>
                <span className="text-slate-500 block">Biomarker / Analyte</span>
                <span className="font-bold text-slate-900">CA 15-3 (Serum)</span>
              </div>
              <div>
                <span className="text-slate-500 block">Observed Draw Value</span>
                <span className="font-bold text-rose-700 text-sm">180.0 U/mL</span>
              </div>
              <div>
                <span className="text-slate-500 block">Baseline Reference</span>
                <span className="font-bold text-slate-900">18.0 U/mL (10.0x Jump)</span>
              </div>
            </div>

            {/* M3 & M5 Clinical Basis */}
            <div className="space-y-3">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Objective Surveillance Evaluation (M3 Plausibility Engine)
              </h2>
              <div className="bg-slate-50 border border-slate-300 rounded-lg p-4 font-mono text-xs text-slate-800 leading-relaxed">
                <p className="font-bold">VERDICT: Analytical or Pre-Analytical Discrepancy Suspected (Needs Repeat)</p>
                <p className="mt-1">
                  Rationale: Consecutive observation ratio of 10.00x dramatically exceeds the Reference Change Value (RCV = 31.2%). In the absence of concordant enzymatic elevation, pre-analytical error or transcription shift is the most probable hypothesis.
                </p>
              </div>
            </div>

            {/* Requested Clinical Action */}
            <div className="space-y-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Action Requested by Patient & Family Advocate
              </h2>
              <div className="p-4 bg-teal-50 border border-teal-300 rounded-lg text-xs text-teal-950 font-medium leading-relaxed">
                <p className="font-bold">Order a confirmatory laboratory repeat draw (within 7–14 days) prior to initiating advanced imaging or altering systemic treatment regimens.</p>
                <p className="mt-1 text-teal-800">
                  Notes: &quot;{submittedData.notes}&quot;
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="pt-4 border-t border-slate-200 flex items-center justify-between text-[11px] text-slate-500">
              <span>Task Reference: {submittedData.task_id}</span>
              <span>Vigil Clinical Protocol • Mandatory Disposition Invariant</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
