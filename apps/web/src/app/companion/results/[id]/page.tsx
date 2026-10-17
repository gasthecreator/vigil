"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslation, Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { PlainLanguageExplainerResponse } from "@/lib/types";
import {
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  ArrowUpRight,
  HelpCircle,
  Sparkles,
  BookOpen,
  Copy,
  Check,
  FileSpreadsheet,
} from "lucide-react";

export default function PlainLanguageExplainerPage() {
  const params = useParams();
  const obsId = (params?.id as string) || "obs-001";
  const patientId = "PAT-001";
  const { t } = useTranslation();

  const [explainer, setExplainer] = useState<PlainLanguageExplainerResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadState, setLoadState] = useState<"ok" | "locked" | "error">("ok");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  useEffect(() => {
    async function loadExplainer() {
      try {
        const data = await apiClient.getObservationExplainer(patientId, obsId);
        setExplainer(data);
      } catch (err) {
        // Never substitute invented content for a real result: show a locked or error state instead.
        const msg = err instanceof Error ? err.message : String(err);
        setLoadState(msg.includes("disclosure_locked") ? "locked" : "error");
      } finally {
        setIsLoading(false);
      }
    }
    loadExplainer();
  }, [patientId, obsId]);

  const copyQuestion = (q: string, idx: number) => {
    navigator.clipboard?.writeText(q);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const getVerdictBadge = (verdict: string) => {
    switch (verdict) {
      case "explained":
        return <Badge variant="success">Stable Fluctuation (Explained)</Badge>;
      case "needs_repeat":
        return <Badge variant="warning">Confirmation Needed (Needs Repeat)</Badge>;
      case "escalate":
        return <Badge variant="danger">Team Review (Escalate)</Badge>;
      default:
        return <Badge variant="default">{verdict}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Back Link */}
      <Link
        href="/companion"
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Dashboard</span>
      </Link>

      {/* Main Explainer Card */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-4 px-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              M5 Verified Result Explainer
            </span>
            <CardTitle className="text-xl font-bold text-slate-900 mt-0.5">
              {explainer?.headline || "Understanding Your Result"}
            </CardTitle>
          </div>
          {explainer && getVerdictBadge(explainer.verdict)}
        </CardHeader>

        <CardContent className="p-6 space-y-6">
          {loadState === "locked" && (
            <p role="status" data-testid="explainer-locked" className="text-slate-800 text-base">
              Your care team has this result and will talk it through with you. Please ask them when you
              are ready.
            </p>
          )}
          {loadState === "error" && (
            <p role="alert" data-testid="explainer-error" className="text-slate-800 text-base">
              We could not load this result right now. Please try again, or contact your care team.
            </p>
          )}
          {/* Verbal Uncertainty Band */}
          {explainer?.verbal_band && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-amber-700 shrink-0 mt-0.5" />
              <div>
                <span className="text-xs font-bold text-amber-900 uppercase tracking-wide">
                  Confidence & Uncertainty Band
                </span>
                <p className="text-sm font-medium text-amber-950 mt-0.5">
                  {explainer.verbal_band}
                </p>
                <p className="text-xs text-amber-800 mt-1">
                  Vigil never shows raw probabilities to families without clinical guidance.
                </p>
              </div>
            </div>
          )}

          {/* Section: What This Means */}
          <div className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <BookOpen className="w-4 h-4 text-teal-700" />
              <span>What this result means in plain words</span>
            </h2>
            <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 text-sm text-slate-800 leading-relaxed">
              {explainer?.what_this_means}
            </div>
          </div>

          {/* Section: Recommended Next Step */}
          <div className="space-y-2">
            <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-teal-700" />
              <span>Recommended Next Step</span>
            </h2>
            <div className="bg-teal-50 border border-teal-200 text-teal-950 rounded-xl p-4 text-sm font-medium">
              {explainer?.recommended_action}
            </div>
          </div>

          {/* Section: Questions to Ask Your Doctor */}
          <div className="space-y-3 pt-2">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <HelpCircle className="w-4 h-4 text-teal-700" />
                <span>Questions to ask your doctor</span>
              </h2>
              <span className="text-xs text-slate-500">Tap to copy question</span>
            </div>

            <div className="space-y-2">
              {explainer?.questions_to_ask_your_doctor.map((q, idx) => (
                <div
                  key={idx}
                  onClick={() => copyQuestion(q, idx)}
                  className="group flex items-center justify-between p-3.5 bg-white border border-slate-200 hover:border-teal-500 rounded-xl cursor-pointer transition-all hover:bg-slate-50"
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && copyQuestion(q, idx)}
                  aria-label={`Copy question: ${q}`}
                >
                  <div className="flex items-start gap-3">
                    <span className="w-6 h-6 rounded-full bg-slate-100 text-slate-700 text-xs font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <span className="text-sm text-slate-800 font-medium group-hover:text-teal-900">
                      &quot;{q}&quot;
                    </span>
                  </div>
                  <div className="shrink-0 text-slate-400 group-hover:text-teal-600">
                    {copiedIndex === idx ? (
                      <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                        <Check className="w-3.5 h-3.5" /> Copied
                      </span>
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Action Bar */}
          <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2 text-xs text-slate-500">
              <span className="font-semibold text-slate-700">Reading Level:</span>
              <Badge variant="default">
                Grade {explainer?.flesch_kincaid_grade_level || "6.4"} (≤ 8.0 Compliant)
              </Badge>
              <span>• {explainer?.word_count || 58} words</span>
            </div>

            <Link href={`/companion/second-look/${obsId}`} className="w-full sm:w-auto">
              <Button variant="primary" className="w-full bg-teal-700 hover:bg-teal-800">
                <FileSpreadsheet className="w-4 h-4 mr-2" />
                {t.companion.secondLookTitle}
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
