"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation, Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import {
  ShieldAlert,
  Unlock,
  ChevronRight,
  Activity,
  Share2,
  FileSearch,
  CheckCircle2,
  Clock,
  Sparkles,
  HelpCircle,
} from "lucide-react";

export default function CompanionDashboard() {
  const { t } = useTranslation();
  const patientId = "PAT-001"; // Default patient profile for seeded companion session

  const [isUnlocked, setIsUnlocked] = useState<boolean>(false);
  const [isUnlocking, setIsUnlocking] = useState<boolean>(false);
  const [observations, setObservations] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        const obs = await apiClient.listObservations(patientId);
        setObservations(obs || []);
      } catch (err) {
        console.error("Failed to load companion observations:", err);
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [patientId]);

  const handleUnlock = async () => {
    setIsUnlocking(true);
    try {
      await apiClient.unlockDisclosure(patientId, { reason: "patient_opt_in_reveal" });
      setIsUnlocked(true);
    } catch (err) {
      console.error("Failed to unlock disclosure:", err);
      // Fallback for offline or local preview
      setIsUnlocked(true);
    } finally {
      setIsUnlocking(false);
    }
  };

  const latestObs = observations.length > 0 ? observations[0] : null;

  return (
    <div className="space-y-6">
      {/* Welcome & Status */}
      <div className="bg-gradient-to-r from-teal-700 to-cyan-800 rounded-2xl p-6 text-white shadow-md">
        <h1 className="text-xl md:text-2xl font-bold tracking-tight">
          {t.companion.title}
        </h1>
        <p className="text-teal-100 text-sm mt-1 max-w-xl">
          {t.companion.subtitle}
        </p>
        <div className="flex items-center gap-2 mt-4 text-xs bg-white/10 backdrop-blur-sm w-fit px-3 py-1.5 rounded-full">
          <CheckCircle2 className="w-3.5 h-3.5 text-teal-300" />
          <span>Surveillance Monitoring Active • Routine Schedule</span>
        </div>
      </div>

      {/* Bad-News Mode: Protected Results Disclosure (Master Plan §6.8, §10, §11) */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-3.5 px-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-amber-600" aria-hidden="true" />
              <CardTitle className="text-base font-bold text-slate-900">
                {t.companion.badNewsModeTitle}
              </CardTitle>
            </div>
            <Badge variant={isUnlocked ? "success" : "warning"}>
              {isUnlocked ? "Unlocked" : "Gated Disclosure"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-5">
          {!isUnlocked ? (
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center shrink-0 mt-0.5">
                  <Clock className="w-5 h-5" />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">
                    New Surveillance Results Ready
                  </h2>
                  <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                    {t.companion.badNewsWarning}
                  </p>
                </div>
              </div>
              <div className="pt-2 flex flex-col sm:flex-row gap-3">
                <Button
                  variant="primary"
                  onClick={handleUnlock}
                  disabled={isUnlocking}
                  className="bg-teal-700 hover:bg-teal-800 text-white font-medium"
                >
                  <Unlock className="w-4 h-4 mr-2" />
                  {isUnlocking ? "Unlocking..." : t.companion.unlockResults}
                </Button>
                <Link href="/companion/symptoms">
                  <Button variant="outline" className="w-full sm:w-auto">
                    Record Symptoms First
                  </Button>
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-800 uppercase tracking-wider">
                    Latest Lab Update
                  </span>
                  <span className="text-xs text-slate-500">
                    {latestObs?.specimen_collected_at
                      ? new Date(latestObs.specimen_collected_at).toLocaleDateString()
                      : "Recent"}
                  </span>
                </div>
                <h2 className="text-base font-bold text-slate-900 mt-1">
                  CA 15-3 Biomarker Surveillance Draw
                </h2>
                {/* Verbal Uncertainty Band — Never raw percentages to families */}
                <div className="mt-2 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-100 text-amber-900 text-xs font-medium">
                  <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                  <span>Analytical Uncertainty (Suspected Lab Variation)</span>
                </div>
                <p className="text-xs text-slate-600 mt-2 leading-relaxed">
                  A sudden change was observed that likely reflects normal lab equipment variation rather than a true shift. Your doctor has requested a confirmation repeat test.
                </p>
                <div className="mt-4 flex flex-wrap gap-2.5">
                  <Link href={`/companion/results/${latestObs?.id || "obs-001"}`}>
                    <Button variant="primary" size="sm" className="bg-teal-700 hover:bg-teal-800">
                      Explain This Result
                      <ChevronRight className="w-4 h-4 ml-1" />
                    </Button>
                  </Link>
                  <Link href={`/companion/second-look/${latestObs?.id || "obs-001"}`}>
                    <Button variant="outline" size="sm">
                      {t.companion.requestSecondLook}
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Action Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* 1. Symptom Diary */}
        <Link href="/companion/symptoms" className="group block">
          <Card className="h-full border-slate-200 hover:border-teal-500 hover:shadow-md transition-all">
            <CardContent className="p-4 flex flex-col justify-between h-full">
              <div>
                <div className="w-9 h-9 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Activity className="w-5 h-5" />
                </div>
                <h2 className="text-sm font-bold text-slate-900">
                  {t.companion.symptomDiaryTitle}
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Log body changes with voice notes or text.
                </p>
              </div>
              <div className="mt-3 flex items-center text-xs font-semibold text-teal-700">
                <span>{t.companion.logSymptom}</span>
                <ChevronRight className="w-3.5 h-3.5 ml-0.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* 2. Second-Look Request */}
        <Link href={`/companion/second-look/${latestObs?.id || "obs-001"}`} className="group block">
          <Card className="h-full border-slate-200 hover:border-teal-500 hover:shadow-md transition-all">
            <CardContent className="p-4 flex flex-col justify-between h-full">
              <div>
                <div className="w-9 h-9 rounded-lg bg-cyan-100 text-cyan-700 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <FileSearch className="w-5 h-5" />
                </div>
                <h2 className="text-sm font-bold text-slate-900">
                  {t.companion.secondLookTitle}
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Request a clinical second-look confirmation summary.
                </p>
              </div>
              <div className="mt-3 flex items-center text-xs font-semibold text-cyan-700">
                <span>Generate Summary</span>
                <ChevronRight className="w-3.5 h-3.5 ml-0.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Card>
        </Link>

        {/* 3. Caregiver Sharing */}
        <Link href="/companion/share" className="group block">
          <Card className="h-full border-slate-200 hover:border-teal-500 hover:shadow-md transition-all">
            <CardContent className="p-4 flex flex-col justify-between h-full">
              <div>
                <div className="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <Share2 className="w-5 h-5" />
                </div>
                <h2 className="text-sm font-bold text-slate-900">
                  {t.companion.caregiverSharingTitle}
                </h2>
                <p className="text-xs text-slate-500 mt-1">
                  Grant scoped, revocable access to family members.
                </p>
              </div>
              <div className="mt-3 flex items-center text-xs font-semibold text-indigo-700">
                <span>Manage Shares</span>
                <ChevronRight className="w-3.5 h-3.5 ml-0.5 group-hover:translate-x-1 transition-transform" />
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* Questions for Your Doctor Help Banner */}
      <div className="bg-slate-100 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
        <HelpCircle className="w-5 h-5 text-teal-700 shrink-0 mt-0.5" />
        <div className="text-xs text-slate-700">
          <span className="font-bold text-slate-900">Advocating for your care: </span>
          Vigil prepares plain-language questions you can ask during your clinic visit. Click &quot;Explain This Result&quot; to review them.
        </div>
      </div>
    </div>
  );
}
