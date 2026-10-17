"use client";

import React, { useState } from "react";
import { useTranslation, Badge, Button, Card, CardHeader, CardTitle, CardContent } from "@vigil/ui";
import { FollowUpTaskResponse } from "@/lib/types";
import { apiClient } from "@/lib/api";
import { CheckSquare, PhoneCall, Clock, AlertTriangle, CheckCircle2 } from "lucide-react";

interface FollowUpBoardProps {
  tasks: FollowUpTaskResponse[];
  onTaskUpdated: () => void;
}

export const FollowUpBoard: React.FC<FollowUpBoardProps> = ({ tasks, onTaskUpdated }) => {
  const { t } = useTranslation();
  const [updatingTaskId, setUpdatingTaskId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const handleUpdateStatus = async (taskId: string, newStatus: string) => {
    setUpdatingTaskId(taskId);
    setFeedback(null);
    try {
      await apiClient.transitionFollowUpTask(taskId, {
        target_status: newStatus,
        reason: `Task marked as ${newStatus} by clinician via workstation.`,
      });
      setFeedback(`Task ${taskId} updated to ${newStatus}.`);
      onTaskUpdated();
    } catch {
      setFeedback("Failed to update task status.");
    } finally {
      setUpdatingTaskId(null);
    }
  };

  return (
    <Card className="border-slate-200">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckSquare className="w-5 h-5 text-emerald-700" />
            {t.followUp.boardTitle}
          </CardTitle>
          <span className="text-xs bg-slate-100 text-slate-800 font-bold px-2.5 py-0.5 rounded-full border border-slate-300">
            {tasks.length} {t.followUp.openTasksCount}
          </span>
        </div>
      </CardHeader>

      <CardContent>
        {feedback && (
          <div className="mb-3 p-2.5 bg-emerald-50 text-emerald-800 text-xs rounded border border-emerald-200 font-semibold flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            {feedback}
          </div>
        )}

        {tasks.length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-sm">
            <CheckCircle2 className="w-8 h-8 text-emerald-500 mx-auto mb-2" />
            All scheduled follow-up tasks and reminder loops are up to date.
          </div>
        ) : (
          <div className="space-y-2.5">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className="p-3.5 bg-slate-50 rounded-lg border border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:border-slate-300 transition-colors"
              >
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge
                      variant={
                        task.escalation_level >= 2
                          ? "danger"
                          : task.escalation_level === 1
                          ? "warning"
                          : "default"
                      }
                    >
                      {task.escalation_level >= 2
                        ? "URGENT (ESC L2+)"
                        : task.escalation_level === 1
                        ? "HIGH (ESC L1)"
                        : "STANDARD"}
                    </Badge>
                    <span className="text-xs font-mono font-bold text-slate-900">{task.patient_id}</span>
                    <span className="text-xs font-mono text-slate-500">[{task.task_type}]</span>
                  </div>

                  <p className="text-xs text-slate-600 flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5 text-slate-400" />
                    Due by {new Date(task.due_date).toLocaleDateString()}
                    {task.status && (
                      <span className="ml-2 font-semibold uppercase text-slate-700">Status: {task.status}</span>
                    )}
                  </p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 self-start sm:self-auto">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleUpdateStatus(task.task_id, "in_progress")}
                    disabled={updatingTaskId === task.task_id || task.status === "in_progress"}
                    className="flex items-center gap-1 text-xs"
                  >
                    <PhoneCall className="w-3.5 h-3.5 text-slate-600" />
                    {t.followUp.contactPatient}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => handleUpdateStatus(task.task_id, "completed")}
                    disabled={updatingTaskId === task.task_id || task.status === "completed"}
                    className="text-xs"
                  >
                    {t.followUp.markCompleted}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
