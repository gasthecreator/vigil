"use client";

import React, { useState } from "react";
import { useTranslation, Badge, Button, Modal, Card, CardHeader, CardTitle, CardContent } from "@vigil/ui";
import { AlertSummary, AlertAcknowledgeRequest } from "@/lib/types";
import { apiClient } from "@/lib/api";
import { Bell, CheckCircle, AlertTriangle, ShieldCheck } from "lucide-react";

interface AlertInboxProps {
  alerts: AlertSummary[];
  onAcknowledgeSuccess: () => void;
}

export const AlertInbox: React.FC<AlertInboxProps> = ({ alerts, onAcknowledgeSuccess }) => {
  const { t } = useTranslation();
  const [selectedAlert, setSelectedAlert] = useState<AlertSummary | null>(null);
  const [disposition, setDisposition] = useState<string>("confirmed_progression");
  const [rationaleText, setRationaleText] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleAcknowledge = async () => {
    if (!selectedAlert) return;
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const ackReq: AlertAcknowledgeRequest = {
        disposition,
        rationale_text: rationaleText || "Clinician reviewed and acknowledged via workstation.",
      };
      await apiClient.acknowledgeAlert(selectedAlert.id, ackReq);
      setSelectedAlert(null);
      setRationaleText("");
      onAcknowledgeSuccess();
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to submit alert acknowledgement.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Bell className="w-5 h-5 text-amber-600" />
            {t.alerts.inboxTitle}
          </CardTitle>
          <span className="text-xs bg-amber-100 text-amber-900 font-bold px-2.5 py-0.5 rounded-full border border-amber-300">
            {alerts.length} Pending
          </span>
        </div>
      </CardHeader>

      <CardContent>
        {alerts.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            <CheckCircle className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            No active unacknowledged alerts in the surveillance queue.
          </div>
        ) : (
          <div className="space-y-2.5">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-300 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        alert.severity === "urgent"
                          ? "urgent"
                          : alert.severity === "review"
                          ? "review"
                          : "watch"
                      }
                    >
                      {alert.severity.toUpperCase()}
                    </Badge>
                    <span className="text-xs font-mono text-slate-500">{alert.id}</span>
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{alert.trigger_reason}</p>
                  <p className="text-xs text-slate-500">
                    Created at {new Date(alert.created_at).toLocaleString()}
                  </p>
                </div>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setSelectedAlert(alert)}
                  className="self-start sm:self-auto"
                >
                  {t.alerts.acknowledgeButton}
                </Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>

      {/* Required Acknowledgement Disposition Modal */}
      <Modal
        isOpen={!!selectedAlert}
        onClose={() => setSelectedAlert(null)}
        title={t.alerts.acknowledgeModalTitle}
        description={`Alert ${selectedAlert?.id}: ${selectedAlert?.trigger_reason}`}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              {t.alerts.dispositionPrompt}
            </label>
            <div className="space-y-2">
              {[
                { value: "confirmed_progression", label: t.alerts.dispositionConfirmed },
                { value: "repeat_scheduled", label: t.alerts.dispositionRepeatScheduled },
                { value: "escalated_to_imaging", label: t.alerts.dispositionEscalatedToImaging },
              ].map((opt) => (
                <label
                  key={opt.value}
                  className={`flex items-start gap-2.5 p-3 rounded-lg border cursor-pointer transition-colors ${
                    disposition === opt.value
                      ? "bg-emerald-50 border-emerald-500 text-emerald-950"
                      : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  <input
                    type="radio"
                    name="disposition"
                    value={opt.value}
                    checked={disposition === opt.value}
                    onChange={(e) => setDisposition(e.target.value)}
                    className="mt-0.5 text-emerald-600 focus:ring-emerald-500"
                  />
                  <span className="text-xs font-medium">{opt.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="ack-notes" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
              {t.alerts.notesPrompt}
            </label>
            <textarea
              id="ack-notes"
              rows={3}
              value={rationaleText}
              onChange={(e) => setRationaleText(e.target.value)}
              placeholder="Record clinical assessment and rationale..."
              className="w-full text-xs p-2.5 rounded-lg border border-slate-300 focus:ring-2 focus:ring-emerald-600 focus:outline-none"
            />
          </div>

          {errorMsg && (
            <div className="p-2.5 bg-red-50 text-red-800 text-xs rounded border border-red-200 font-medium">
              {errorMsg}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setSelectedAlert(null)}>
              {t.common.cancel}
            </Button>
            <Button onClick={handleAcknowledge} isLoading={isSubmitting}>
              {t.alerts.submitAcknowledgement}
            </Button>
          </div>
        </div>
      </Modal>
    </Card>
  );
};
