"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useTranslation, Button, Input, Modal } from "@vigil/ui";
import { apiClient, queueOfflineMutation } from "@/lib/api";
import { Keyboard, CheckCircle2, AlertCircle } from "lucide-react";

interface ObservationIntakeModalProps {
  isOpen: boolean;
  onClose: () => void;
  patientId: string;
  onIntakeSuccess: () => void;
}

export const ObservationIntakeModal: React.FC<ObservationIntakeModalProps> = ({
  isOpen,
  onClose,
  patientId,
  onIntakeSuccess,
}) => {
  const { t } = useTranslation();
  const [analyteCode, setAnalyteCode] = useState<string>("ca_15_3");
  const [value, setValue] = useState<string>("");
  const [unit, setUnit] = useState<string>("U/mL");
  const [specimenDate, setSpecimenDate] = useState<string>(new Date().toISOString().slice(0, 16));
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [isError, setIsError] = useState<boolean>(false);

  // Update default unit based on analyte
  useEffect(() => {
    if (analyteCode === "ca_15_3") setUnit("U/mL");
    else if (analyteCode === "alt" || analyteCode === "ast" || analyteCode === "alp") setUnit("U/L");
    else if (analyteCode === "cea") setUnit("ng/mL");
    else if (analyteCode === "creatinine") setUnit("umol/L");
    else if (analyteCode === "calcium") setUnit("mmol/L");
  }, [analyteCode]);

  const handleSubmit = useCallback(async () => {
    const numVal = parseFloat(value);
    if (isNaN(numVal) || numVal <= 0) {
      setIsError(true);
      setFeedback("Please enter a valid positive numerical measurement.");
      return;
    }

    setIsSubmitting(true);
    setFeedback(null);
    setIsError(false);

    const payload = {
      analyte_code: analyteCode,
      value: numVal,
      unit,
      specimen_collected_at: new Date(specimenDate).toISOString(),
    };

    try {
      // Attempt live ingestion through apiClient
      await apiClient.ingestObservation(patientId, payload);
      setFeedback("Observation recorded successfully and ingested into surveillance pipeline.");
      setTimeout(() => {
        onIntakeSuccess();
        onClose();
      }, 1000);
    } catch {
      // Network failure or offline -> fallback to offline queue
      queueOfflineMutation({
        client_mutation_id: `mut-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
        entity_type: "observation",
        action: "create",
        patient_id: patientId,
        client_updated_at: new Date().toISOString(),
        payload,
      });
      setFeedback(t.intake.offlineSavedNotice);
      setTimeout(() => {
        onIntakeSuccess();
        onClose();
      }, 1000);
    } finally {
      setIsSubmitting(false);
    }
  }, [value, analyteCode, unit, specimenDate, patientId, onClose, onIntakeSuccess, t]);

  // Keyboard shortcut listener (Alt+S or Ctrl+S to save)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.altKey || e.ctrlKey) && e.key.toLowerCase() === "s" && isOpen) {
        e.preventDefault();
        handleSubmit();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleSubmit]);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={t.intake.drawerTitle}
      description={`Patient: ${patientId}`}
    >
      <div className="space-y-4">
        {/* Keyboard shortcut tip */}
        <div className="flex items-center gap-2 p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
          <Keyboard className="w-4 h-4 text-emerald-700 flex-shrink-0" />
          <span>{t.intake.fastIntakeTip}</span>
        </div>

        {/* Form Controls */}
        <div className="space-y-3">
          <div>
            <label htmlFor="analyte-select" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              {t.intake.analyteCode}
            </label>
            <select
              id="analyte-select"
              value={analyteCode}
              onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setAnalyteCode(e.target.value)}
              className="w-full h-11 px-3 text-sm rounded-md border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600"
            >
              <option value="ca_15_3">CA 15-3 (Cancer Antigen 15-3)</option>
              <option value="alt">ALT (Alanine Aminotransferase — Liver)</option>
              <option value="ast">AST (Aspartate Aminotransferase)</option>
              <option value="alp">ALP (Alkaline Phosphatase — Bone)</option>
              <option value="cea">CEA (Carcinoembryonic Antigen)</option>
              <option value="creatinine">Creatinine (Renal Safety)</option>
              <option value="calcium">Calcium (Bone Metastasis)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <Input
              label={t.intake.value}
              type="number"
              step="any"
              placeholder="e.g. 24.5"
              value={value}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setValue(e.target.value)}
              autoFocus
            />
            <Input label={t.intake.unit} value={unit} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setUnit(e.target.value)} />
          </div>

          <div>
            <label htmlFor="specimen-date" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              {t.intake.specimenDate}
            </label>
            <input
              id="specimen-date"
              type="datetime-local"
              value={specimenDate}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSpecimenDate(e.target.value)}
              className="w-full h-11 px-3 text-sm rounded-md border border-slate-300 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600"
            />
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
          <Button onClick={handleSubmit} isLoading={isSubmitting}>
            {t.intake.submitObservation}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
