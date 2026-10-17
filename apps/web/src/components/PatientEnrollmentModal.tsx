"use client";

import React, { useState } from "react";
import { useTranslation, Button, Input, Modal } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { UserPlus, CheckCircle2, AlertCircle } from "lucide-react";

interface PatientEnrollmentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEnrollmentSuccess: (newPatientId: string) => void;
}

export const PatientEnrollmentModal: React.FC<PatientEnrollmentModalProps> = ({
  isOpen,
  onClose,
  onEnrollmentSuccess,
}) => {
  const { t } = useTranslation();
  const [mrn, setMrn] = useState("");
  const [age, setAge] = useState<string>("52");
  const [stage, setStage] = useState<string>("Stage II");
  const [subtype, setSubtype] = useState<string>("HR+HER2-");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);

  const handleEnroll = async () => {
    const ageNum = parseInt(age, 10);
    if (isNaN(ageNum) || ageNum < 18 || ageNum > 100) {
      setIsError(true);
      setFeedback("Please provide a valid age between 18 and 100.");
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);
    setIsError(false);

    try {
      // 1. Enrol Patient
      const patient = await apiClient.createPatient({
        age: ageNum,
        mrn: mrn.trim() || undefined,
        status: "active",
      });

      // 2. Register Mandatory Clinical Care Consent
      await apiClient.grantConsent(patient.id, {
        granted: true,
        scope: "clinical_care",
      });

      setFeedback(`Patient ${patient.id} successfully enrolled with clinical care consent.`);
      setTimeout(() => {
        onEnrollmentSuccess(patient.id);
        onClose();
      }, 700);
    } catch (err: any) {
      setIsError(true);
      setFeedback(err.message || "Failed to enrol patient.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Enrol New Surveillance Patient"
      description="Register patient baseline demographics and record clinical care consent."
    >
      <div className="space-y-4">
        <div className="space-y-3">
          <Input
            label="Hospital Medical Record Number (MRN)"
            placeholder="e.g. MRN-UCH-2026-981"
            value={mrn}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setMrn(e.target.value)}
            helperText="MRN is encrypted at rest using AES-GCM/Fernet with blind indexing."
          />

          <Input
            label="Patient Age at Diagnosis"
            type="number"
            min={18}
            max={100}
            value={age}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setAge(e.target.value)}
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="stage-select" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Clinical Stage
              </label>
              <select
                id="stage-select"
                value={stage}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setStage(e.target.value)}
                className="w-full h-11 px-3 text-sm rounded-md border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600"
              >
                <option value="Stage I">Stage I</option>
                <option value="Stage II">Stage II (Early Invasive)</option>
                <option value="Stage III">Stage III (Locally Advanced)</option>
                <option value="Stage IV">Stage IV (De Novo Metastatic)</option>
              </select>
            </div>

            <div>
              <label htmlFor="subtype-select" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                Molecular Subtype
              </label>
              <select
                id="subtype-select"
                value={subtype}
                onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setSubtype(e.target.value)}
                className="w-full h-11 px-3 text-sm rounded-md border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600"
              >
                <option value="HR+HER2-">Luminal A/B (HR+HER2-)</option>
                <option value="TNBC">Triple-Negative (TNBC)</option>
                <option value="HER2+">HER2-Enriched (HER2+)</option>
              </select>
            </div>
          </div>
        </div>

        {feedback && (
          <div
            className={`p-3 rounded text-xs font-semibold flex items-center gap-2 ${
              isError
                ? "bg-red-50 text-red-800 border border-red-200"
                : "bg-emerald-50 text-emerald-800 border border-emerald-200"
            }`}
          >
            {isError ? <AlertCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
            {feedback}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <Button variant="outline" onClick={onClose}>
            {t.common.cancel}
          </Button>
          <Button onClick={handleEnroll} isLoading={isSubmitting}>
            Enrol & Grant Consent
          </Button>
        </div>
      </div>
    </Modal>
  );
};
