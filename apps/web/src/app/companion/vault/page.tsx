"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslation, Button, Card, CardContent, CardHeader, CardTitle, Badge } from "@vigil/ui";
import { apiClient } from "@/lib/api";
import { ArrowLeft, FileUp, AlertTriangle } from "lucide-react";

const PATIENT_ID = "PAT-001";

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
  notice: string;
  created_at: string;
};

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || "");
      const comma = text.indexOf(",");
      resolve(comma >= 0 ? text.slice(comma + 1) : text);
    };
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}

export default function LabVaultPage() {
  const { t } = useTranslation();
  const [drafts, setDrafts] = useState<OcrDraft[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const rows = await apiClient.listOcrDrafts(PATIENT_ID);
      setDrafts(rows as OcrDraft[]);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not load drafts.");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onFile(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const content_base64 = await fileToBase64(file);
      await apiClient.createOcrDraft(PATIENT_ID, {
        filename: file.name,
        content_type: file.type || "application/pdf",
        content_base64,
      });
      await load();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }

  return (
    <div className="space-y-4">
      <Link
        href="/companion"
        className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Dashboard
      </Link>

      <div>
        <h1 className="text-xl font-bold text-slate-900">{t.companion.labVaultTitle}</h1>
        <p className="text-sm text-slate-600 mt-1">{t.companion.labVaultSubtitle}</p>
      </div>

      <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-950 flex gap-2">
        <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" aria-hidden="true" />
        <p>{t.companion.labVaultNotice}</p>
      </div>

      <Card>
        <CardHeader className="py-3 px-4">
          <CardTitle className="text-sm">{t.companion.labVaultUpload}</CardTitle>
        </CardHeader>
        <CardContent className="px-4 pb-4">
          <label className="flex items-center gap-2 text-sm">
            <FileUp className="w-4 h-4 text-teal-700" aria-hidden="true" />
            <input
              type="file"
              accept="image/png,image/jpeg,application/pdf"
              onChange={onFile}
              disabled={busy}
              aria-label={t.companion.labVaultUpload}
            />
          </label>
          {busy && <p className="text-xs text-slate-500 mt-2">Reading the file on this device…</p>}
        </CardContent>
      </Card>

      {error && (
        <p className="text-sm text-rose-800 bg-rose-50 border border-rose-200 rounded-md p-3" role="alert">
          {error}
        </p>
      )}

      <ul className="space-y-3">
        {drafts.map((draft) => (
          <li key={draft.id}>
            <Card>
              <CardContent className="p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-semibold text-slate-900">{draft.filename}</span>
                  <Badge variant={draft.status === "pending" ? "warning" : "default"}>
                    {draft.status === "pending" ? t.companion.labVaultPending : draft.status}
                  </Badge>
                </div>
                <p className="text-xs text-slate-500">Engine: {draft.engine}</p>
                {draft.suggestion?.analyte_code && (
                  <p className="text-sm text-slate-800">
                    Suggestion (not in record): {draft.suggestion.analyte_code}{" "}
                    {draft.suggestion.value} {draft.suggestion.unit}
                  </p>
                )}
                {(draft.confusion_flags || []).length > 0 && (
                  <ul className="text-xs text-amber-900 bg-amber-50 rounded-md p-2 space-y-1">
                    {draft.confusion_flags.map((flag) => (
                      <li key={`${flag.field}-${flag.reason}`}>
                        Check {flag.field}: {flag.reason}
                      </li>
                    ))}
                  </ul>
                )}
                {draft.extracted_text && (
                  <pre className="text-[11px] bg-slate-50 border border-slate-100 rounded-md p-2 overflow-x-auto whitespace-pre-wrap">
                    {draft.extracted_text}
                  </pre>
                )}
              </CardContent>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
