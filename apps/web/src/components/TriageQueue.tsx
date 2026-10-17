"use client";

import React, { useState, useMemo } from "react";
import { useTranslation, Badge, Button, Input } from "@vigil/ui";
import { TriagePatientViewModel } from "@/lib/types";
import { Search, Plus, AlertCircle, Clock, ChevronRight, Filter } from "lucide-react";

interface TriageQueueProps {
  patients: TriagePatientViewModel[];
  selectedPatientId: string | null;
  onSelectPatient: (patientId: string) => void;
  onOpenEnrollment: () => void;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  patients,
  selectedPatientId,
  onSelectPatient,
  onOpenEnrollment,
}) => {
  const { t } = useTranslation();
  const [searchQuery, setSearchQuery] = useState("");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");

  const filteredPatients = useMemo(() => {
    return patients
      .filter((p) => {
        const matchesSearch =
          p.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (p.mrn && p.mrn.toLowerCase().includes(searchQuery.toLowerCase()));

        const matchesUrgency = urgencyFilter === "all" || p.urgencyLevel === urgencyFilter;
        return matchesSearch && matchesUrgency;
      })
      .sort((a, b) => b.compositeUrgencyScore - a.compositeUrgencyScore); // Highest urgency first
  }, [patients, searchQuery, urgencyFilter]);

  return (
    <div className="space-y-4">
      {/* Triage Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">{t.triage.title}</h2>
          <p className="text-xs text-slate-500">{t.triage.subtitle}</p>
        </div>
        <Button onClick={onOpenEnrollment} size="sm" className="flex items-center gap-1.5 self-start sm:self-auto">
          <Plus className="w-4 h-4" />
          Enrol New Patient
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
        <div className="relative flex-1">
          <Search className="w-4 h-4 absolute left-3 top-3.5 text-slate-400" aria-hidden="true" />
          <input
            type="text"
            placeholder="Search by MRN or Patient ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-slate-300 bg-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-600 focus:border-transparent"
            aria-label="Search patients"
          />
        </div>

        {/* Urgency Filter Tabs */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-lg text-xs" role="tablist">
          {["all", "urgent", "high", "medium", "low"].map((filter) => (
            <button
              key={filter}
              role="tab"
              aria-selected={urgencyFilter === filter}
              onClick={() => setUrgencyFilter(filter)}
              className={`px-3 py-1.5 rounded-md font-medium capitalize transition-colors ${
                urgencyFilter === filter
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              {filter}
            </button>
          ))}
        </div>
      </div>

      {/* Patient Triage List */}
      <div className="space-y-2">
        {filteredPatients.length === 0 ? (
          <div className="text-center py-10 bg-slate-50 rounded-xl border border-dashed border-slate-200">
            <AlertCircle className="w-8 h-8 text-slate-400 mx-auto mb-2" />
            <p className="text-sm font-medium text-slate-600">{t.triage.emptyQueue}</p>
          </div>
        ) : (
          filteredPatients.map((patient) => {
            const isSelected = patient.id === selectedPatientId;
            return (
              <div
                key={patient.id}
                onClick={() => onSelectPatient(patient.id)}
                className={`p-4 rounded-xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                  isSelected
                    ? "bg-emerald-50/60 border-emerald-500 shadow-sm ring-1 ring-emerald-500"
                    : "bg-white border-slate-200 hover:border-slate-300 hover:shadow-sm"
                }`}
              >
                {/* Patient Details */}
                <div className="flex items-start gap-3">
                  <div
                    className={`w-2.5 h-12 rounded-full self-stretch ${
                      patient.urgencyLevel === "urgent"
                        ? "bg-red-500"
                        : patient.urgencyLevel === "high"
                        ? "bg-amber-500"
                        : patient.urgencyLevel === "medium"
                        ? "bg-sky-500"
                        : "bg-slate-300"
                    }`}
                    aria-hidden="true"
                  />
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-slate-900 text-sm">{patient.id}</span>
                      {patient.mrn && (
                        <span className="text-xs font-mono bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded border border-slate-200">
                          MRN: {patient.mrn}
                        </span>
                      )}
                      <Badge
                        variant={
                          patient.urgencyLevel === "urgent"
                            ? "urgent"
                            : patient.urgencyLevel === "high"
                            ? "danger"
                            : patient.urgencyLevel === "medium"
                            ? "warning"
                            : "default"
                        }
                      >
                        Urgency Score: {Math.round(patient.compositeUrgencyScore)}
                      </Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 mt-1.5 text-xs text-slate-500">
                      <span>Age: {patient.age}</span>
                      {patient.stage && <span>Stage: {patient.stage}</span>}
                      {patient.subtype && <span>Subtype: {patient.subtype}</span>}
                      {patient.daysSinceLastVisit > 0 && (
                        <span className="flex items-center gap-1 text-slate-600">
                          <Clock className="w-3.5 h-3.5" />
                          Last visit: {patient.daysSinceLastVisit}d ago
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Latest Clinical Observation & Actions */}
                <div className="flex items-center justify-between sm:justify-end gap-3 border-t sm:border-t-0 pt-2 sm:pt-0 border-slate-100">
                  {patient.latestAnalyteCode && (
                    <div className="text-left sm:text-right">
                      <div className="text-xs font-bold text-slate-800">
                        {patient.latestAnalyteCode.toUpperCase()}: {patient.latestAnalyteValue}{" "}
                        {patient.latestAnalyteUnit}
                      </div>
                      {patient.latestM3Action && (
                        <div className="mt-0.5">
                          <Badge variant={patient.latestM3Action}>{patient.latestM3Action}</Badge>
                        </div>
                      )}
                    </div>
                  )}

                  {patient.openTasksCount > 0 && (
                    <span className="text-xs bg-amber-50 text-amber-800 border border-amber-200 px-2 py-1 rounded font-semibold">
                      {patient.openTasksCount} task(s)
                    </span>
                  )}

                  <ChevronRight className="w-5 h-5 text-slate-400 flex-shrink-0" />
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
