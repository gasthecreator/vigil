"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useTranslation, Button, Card, CardContent, CardHeader, CardTitle, Badge } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { AlertTriangle } from "lucide-react";

type ConfusionFlag = { field: string; reason: string };

type OcrDraft = {
  id: string;
  filename: string;
  engine: string;
  status: string;
  extracted_text: string;
  suggestion: {
    analyte_code?: string | null;
    value?: number | null;
    unit?: string | null;
    specimen_collected_at?: string | null;
    flags?: ConfusionFlag[];
  };
  confusion_flags: ConfusionFlag[];
};

export function OcrDraftsPanel({
  patientId,
  onConfirmed,
}: {
  patientId: string;
  onConfirmed: () => void;
}) {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<OcrDraft[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const rows = (await apiClient.listOcrDrafts(patientId)) as OcrDraft[];
      setDrafts(rows.filter((d) => d.status === "pending"));
      setError(null);
    } catch {
      setDrafts([]);
    }
  }, [patientId]);

  useEffect(() => {
    load();
  }, [load]);

  if (drafts.length === 0) {
    return null;
  }

  return (
    <Card className="border-amber-200">
      <CardHeader className="py-3 px-4 bg-amber-50 border-b border-amber-100">
        <CardTitle className="text-sm">{t.companion.labVaultTitle}</CardTitle>
      </CardHeader>
      <CardContent className="p-4 space-y-4">
        <p className="text-xs text-slate-600 flex gap-2">
          <AlertTriangle className="w-4 h-4 shrink-0 text-amber-700" aria-hidden="true" />
          {t.companion.labVaultConfirmHint}
        </p>
        {error && (
          <p className="text-xs text-rose-800" role="alert">
            {error}
          </p>
        )}
        {drafts.map((draft) => (
          <ConfirmForm
            key={draft.id}
            patientId={patientId}
            draft={draft}
            onDone={() => {
              load();
              onConfirmed();
            }}
            onError={setError}
          />
        ))}
      </CardContent>
    </Card>
  );
}

function ConfirmForm({
  patientId,
  draft,
  onDone,
  onError,
}: {
  patientId: string;
  draft: OcrDraft;
  onDone: () => void;
  onError: (message: string) => void;
}) {
  const { t } = useTranslation();
  const flagged = new Set((draft.confusion_flags || []).map((f) => f.field));
  const [analyte, setAnalyte] = useState(draft.suggestion.analyte_code || "");
  const [value, setValue] = useState(
    draft.suggestion.value != null ? String(draft.suggestion.value) : ""
  );
  const [unit, setUnit] = useState(draft.suggestion.unit || "");
  const [when, setWhen] = useState(draft.suggestion.specimen_collected_at || "2026-01-15");
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);

  async function confirm() {
    setBusy(true);
    try {
      await apiClient.confirmOcrDraft(patientId, draft.id, {
        confirmed: true,
        analyte_code: analyte,
        value: Number(value),
        unit,
        specimen_collected_at: new Date(`${when}T00:00:00Z`).toISOString(),
      });
      onDone();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Confirm failed.");
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    setBusy(true);
    try {
      await apiClient.rejectOcrDraft(patientId, draft.id);
      onDone();
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : "Reject failed.");
    } finally {
      setBusy(false);
    }
  }

  const fieldClass = (name: string) =>
    `w-full rounded-md border px-2 py-1 text-sm ${
      flagged.has(name) ? "border-amber-500 bg-amber-50" : "border-slate-200"
    }`;

  return (
    <div className="border border-slate-200 rounded-lg p-3 space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">{draft.filename}</span>
        <Badge variant="warning">pending</Badge>
      </div>
      {draft.extracted_text && (
        <pre className="text-[11px] bg-slate-50 rounded-md p-2 whitespace-pre-wrap max-h-32 overflow-auto">
          {draft.extracted_text}
        </pre>
      )}
      <label className="block text-xs font-medium text-slate-700">
        Analyte
        <input
          className={fieldClass("analyte_code")}
          value={analyte}
          onChange={(e) => setAnalyte(e.target.value)}
        />
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Value
        <input
          className={fieldClass("value")}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          inputMode="decimal"
        />
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Unit
        <input className={fieldClass("unit")} value={unit} onChange={(e) => setUnit(e.target.value)} />
      </label>
      <label className="block text-xs font-medium text-slate-700">
        Specimen date
        <input
          type="date"
          className="w-full rounded-md border border-slate-200 px-2 py-1 text-sm"
          value={when}
          onChange={(e) => setWhen(e.target.value)}
        />
      </label>
      <label className="flex items-start gap-2 text-xs text-slate-800">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => setChecked(e.target.checked)}
        />
        <span>{t.companion.labVaultConfirmHint}</span>
      </label>
      <div className="flex gap-2">
        <Button size="sm" disabled={!checked || busy || !analyte || !value || !unit} onClick={confirm}>
          Confirm into record
        </Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={reject}>
          Reject draft
        </Button>
      </div>
    </div>
  );
}
