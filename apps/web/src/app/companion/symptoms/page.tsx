"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useTranslation, Button, Card, CardHeader, CardTitle, CardContent, Badge } from "@vigil/ui";
import { apiClient, queueOfflineMutation } from "@/lib/api";
import { SymptomResponse } from "@/lib/types";
import {
  ArrowLeft,
  Activity,
  Mic,
  MicOff,
  Send,
  CheckCircle2,
  Clock,
  WifiOff,
  AlertCircle,
} from "lucide-react";

const SYMPTOMS_LIST = [
  { id: "bone_pain", label: "Bone / Back Pain", area: "Skeletal" },
  { id: "fatigue", label: "Severe Fatigue", area: "Systemic" },
  { id: "nausea", label: "Nausea / Vomiting", area: "Digestive" },
  { id: "cough", label: "Persistent Cough / Breathing", area: "Respiratory" },
  { id: "headache", label: "New Headache / Dizziness", area: "Neurological" },
  { id: "swelling", label: "Abdominal / Leg Swelling", area: "Fluid" },
  { id: "appetite_loss", label: "Loss of Appetite / Weight", area: "Metabolic" },
];

const SEVERITY_LEVELS = [
  { level: 1, label: "Mild", desc: "Noticeable, but does not interrupt daily tasks." },
  { level: 2, label: "Moderate", desc: "Somewhat limits normal activities." },
  { level: 3, label: "Severe", desc: "Significantly interferes with daily life." },
  { level: 4, label: "Critical", desc: "Disabling / severe discomfort." },
];

export default function SymptomDiaryPage() {
  const patientId = "PAT-001";
  const { t } = useTranslation();

  const [selectedSymptom, setSelectedSymptom] = useState<string>("bone_pain");
  const [severity, setSeverity] = useState<number>(2);
  const [notes, setNotes] = useState<string>("");
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(true);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [symptomsHistory, setSymptomsHistory] = useState<SymptomResponse[]>([]);

  useEffect(() => {
    // Check Web Speech API availability
    if (typeof window !== "undefined") {
      const hasSpeech = "SpeechRecognition" in window || "webkitSpeechRecognition" in window;
      setSpeechSupported(hasSpeech);
    }

    async function loadSymptoms() {
      try {
        const list = await apiClient.listSymptoms(patientId);
        setSymptomsHistory(list || []);
      } catch (err) {
        console.warn("Could not load online symptoms history:", err);
      }
    }
    loadSymptoms();
  }, [patientId]);

  const handleVoiceToggle = () => {
    if (!speechSupported) {
      setSpeechError("Speech recognition not supported in this browser. Please type your notes below.");
      return;
    }

    try {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SpeechRecognition) {
        setSpeechSupported(false);
        setSpeechError("Speech recognition not supported in this browser; please type your notes.");
        return;
      }

      if (isRecording) {
        setIsRecording(false);
        return;
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = "en-NG";

      recognition.onstart = () => {
        setIsRecording(true);
        setSpeechError(null);
      };

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setNotes((prev) => (prev ? `${prev} ${transcript}` : transcript));
        setIsRecording(false);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition error:", event.error);
        setSpeechError(`Voice input error: ${event.error}. Please type notes directly.`);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognition.start();
    } catch (e: any) {
      setSpeechError("Microphone access unavailable. Please type your notes.");
      setIsRecording(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setSuccessMessage(null);

    const payload = {
      symptom_name: selectedSymptom,
      severity,
      notes: notes || undefined,
      input_modality: isRecording ? "speech" : "text",
    };

    // Check if offline
    if (typeof window !== "undefined" && !navigator.onLine) {
      queueOfflineMutation({
        client_mutation_id: `mut-symp-${Date.now()}`,
        entity_type: "symptom",
        action: "create",
        patient_id: patientId,
        client_updated_at: new Date().toISOString(),
        payload,
      });

      setSuccessMessage("Symptom saved to offline queue. Will sync automatically upon reconnection.");
      setIsSubmitting(false);
      setNotes("");
      return;
    }

    try {
      const created = await apiClient.recordSymptom(patientId, payload);
      setSymptomsHistory((prev) => [created, ...prev]);
      setSuccessMessage("Symptom recorded and shared with your oncology care team.");
      setNotes("");
    } catch (err: any) {
      console.warn("Falling back to local queue:", err);
      queueOfflineMutation({
        client_mutation_id: `mut-symp-${Date.now()}`,
        entity_type: "symptom",
        action: "create",
        patient_id: patientId,
        client_updated_at: new Date().toISOString(),
        payload,
      });
      setSuccessMessage("Saved locally. Will sync when server is reachable.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back to Dashboard */}
      <Link
        href="/companion"
        className="inline-flex items-center gap-1 text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Dashboard</span>
      </Link>

      {/* Main Diary Entry Card */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-4 px-6 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-lg bg-teal-100 text-teal-700 flex items-center justify-center shrink-0">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-900">
                {t.companion.symptomDiaryTitle}
              </CardTitle>
              <p className="text-xs text-slate-500 mt-0.5">
                Track how your body feels so your doctor can detect subtle changes early.
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-6">
          <form onSubmit={handleSubmit} className="space-y-6">
            {successMessage && (
              <div className="p-3.5 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-xl text-xs font-medium flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successMessage}</span>
              </div>
            )}

            {/* 1. Body Map & Symptom Category Selector */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Select Symptom
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {SYMPTOMS_LIST.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => setSelectedSymptom(s.id)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      selectedSymptom === s.id
                        ? "bg-teal-50 border-teal-600 text-teal-950 font-semibold ring-1 ring-teal-600 shadow-sm"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div className="text-xs font-bold">{s.label}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{s.area}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Severity Grade Selector (1 to 4) */}
            <div className="space-y-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                Severity Level
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                {SEVERITY_LEVELS.map((s) => (
                  <button
                    key={s.level}
                    type="button"
                    onClick={() => setSeverity(s.level)}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      severity === s.level
                        ? "bg-teal-50 border-teal-600 text-teal-950 font-semibold ring-1 ring-teal-600 shadow-sm"
                        : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold">{s.label}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-slate-100 font-mono">
                        {s.level}
                      </span>
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">{s.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* 3. Notes with Voice Recognition Input */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Notes / Observations
                </label>
                {/* Voice Input Button */}
                <button
                  type="button"
                  onClick={handleVoiceToggle}
                  className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    isRecording
                      ? "bg-rose-100 text-rose-800 animate-pulse border border-rose-300"
                      : "bg-teal-50 text-teal-700 border border-teal-200 hover:bg-teal-100"
                  }`}
                  aria-label={isRecording ? "Stop voice recording" : "Start voice note recording"}
                >
                  {isRecording ? (
                    <>
                      <MicOff className="w-3.5 h-3.5 text-rose-600" />
                      <span>{t.companion.listening}</span>
                    </>
                  ) : (
                    <>
                      <Mic className="w-3.5 h-3.5 text-teal-600" />
                      <span>{t.companion.recordVoice}</span>
                    </>
                  )}
                </button>
              </div>

              {speechError && (
                <div className="text-xs text-amber-700 bg-amber-50 p-2.5 rounded-lg border border-amber-200 flex items-center gap-1.5">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>{speechError}</span>
                </div>
              )}

              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={3}
                placeholder="Describe how long it has lasted, when it happens, or any other changes you noticed..."
                className="w-full px-3.5 py-2.5 text-sm border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 leading-relaxed"
              />
            </div>

            {/* Submit Button */}
            <div className="pt-2">
              <Button
                type="submit"
                variant="primary"
                disabled={isSubmitting}
                className="w-full sm:w-auto bg-teal-700 hover:bg-teal-800 text-white font-medium"
              >
                <Send className="w-4 h-4 mr-2" />
                {isSubmitting ? "Recording..." : t.companion.logSymptom}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Symptom History List */}
      <Card className="border-slate-200 overflow-hidden shadow-sm">
        <CardHeader className="bg-slate-50 border-b border-slate-200 py-3.5 px-6">
          <CardTitle className="text-sm font-bold text-slate-800">
            Recent Symptom History
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 divide-y divide-slate-100">
          {symptomsHistory.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-500">
              No symptoms recorded yet. Use the form above to log your daily health check.
            </div>
          ) : (
            symptomsHistory.map((item) => (
              <div key={item.id} className="p-4 flex items-center justify-between text-xs hover:bg-slate-50">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900 capitalize">
                      {item.symptom_name.replace("_", " ")}
                    </span>
                    <Badge variant={item.severity >= 3 ? "danger" : "default"}>
                      Severity {item.severity}/4
                    </Badge>
                    <span className="text-slate-400 font-mono text-[10px]">
                      {item.input_modality}
                    </span>
                  </div>
                  {item.notes && <p className="text-slate-600">{item.notes}</p>}
                </div>
                <div className="text-slate-400 text-right whitespace-nowrap ml-4">
                  {new Date(item.recorded_at).toLocaleDateString()}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
