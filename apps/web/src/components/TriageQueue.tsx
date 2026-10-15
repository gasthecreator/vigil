"use client";

import React, { useState } from "react";
import { TriageQueueItem } from "@/lib/types";
import { AlertTriangle, CheckCircle, Search, User, Filter, ChevronRight, Activity } from "lucide-react";

interface TriageQueueProps {
  queue: TriageQueueItem[];
  selectedPatientId: string | null;
  onSelectPatient: (patientId: string) => void;
  onRefresh: () => void;
}

export const TriageQueue: React.FC<TriageQueueProps> = ({
  queue,
  selectedPatientId,
  onSelectPatient,
  onRefresh,
}) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterTier, setFilterTier] = useState<"all" | "alert" | "watch" | "stable">("all");

  const filteredQueue = queue.filter((item) => {
    const matchesSearch =
      item.patient_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      item.subtype.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (filterTier === "alert") return item.latest_risk >= 0.75;
    if (filterTier === "watch") return item.latest_risk >= 0.40 && item.latest_risk < 0.75;
    if (filterTier === "stable") return item.latest_risk < 0.40;
    return true;
  });

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4 flex flex-col h-full">
      {/* Header and Filter Bar */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h2 className="text-base font-bold text-white tracking-wide">
              View 1: Triage Priority Queue
            </h2>
          </div>
          <button
            onClick={onRefresh}
            className="text-xs text-slate-400 hover:text-cyan-400 font-medium transition-colors"
          >
            Refresh Roster
          </button>
        </div>

        {/* Search & Tier Filters */}
        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search by Patient ID or Subtype..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
            <button
              onClick={() => setFilterTier("all")}
              className={`px-2 py-1 rounded transition-colors ${
                filterTier === "all" ? "bg-slate-800 text-white font-semibold" : "text-slate-400 hover:text-white"
              }`}
            >
              All ({queue.length})
            </button>
            <button
              onClick={() => setFilterTier("alert")}
              className={`px-2 py-1 rounded transition-colors ${
                filterTier === "alert"
                  ? "bg-rose-950 text-rose-300 font-semibold border border-rose-800"
                  : "text-rose-400 hover:text-rose-300"
              }`}
            >
              Alerts ({queue.filter((q) => q.latest_risk >= 0.75).length})
            </button>
            <button
              onClick={() => setFilterTier("stable")}
              className={`px-2 py-1 rounded transition-colors ${
                filterTier === "stable"
                  ? "bg-emerald-950 text-emerald-300 font-semibold border border-emerald-800"
                  : "text-emerald-400 hover:text-emerald-300"
              }`}
            >
              Stable
            </button>
          </div>
        </div>
      </div>

      {/* Triage Roster List */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1 max-h-[580px]">
        {filteredQueue.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No patients match current triage filter.
          </div>
        ) : (
          filteredQueue.map((item, index) => {
            const isSelected = item.patient_id === selectedPatientId;
            const isAlert = item.latest_risk >= 0.75;
            const isWatch = item.latest_risk >= 0.40 && item.latest_risk < 0.75;

            return (
              <div
                key={item.patient_id}
                onClick={() => onSelectPatient(item.patient_id)}
                className={`group p-3.5 rounded-xl border transition-all cursor-pointer relative ${
                  isSelected
                    ? "bg-slate-800/90 border-cyan-500 shadow-md shadow-cyan-500/10"
                    : isAlert
                    ? "bg-rose-950/20 hover:bg-rose-950/40 border-rose-900/60"
                    : "bg-slate-950/60 hover:bg-slate-800/50 border-slate-800/80"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center space-x-3 min-w-0">
                    <span className="font-mono text-xs font-bold text-slate-500 w-5">
                      #{index + 1}
                    </span>

                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-semibold text-slate-200 truncate">
                          {item.patient_id.slice(0, 8)}...
                        </span>
                        <span className="text-[11px] text-slate-400">
                          {item.age}yo
                        </span>
                        {item.tumor_stage && (
                          <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 font-mono">
                            Stage {item.tumor_stage}
                          </span>
                        )}
                      </div>

                      <div className="text-[11px] text-slate-400 truncate mt-0.5">
                        {item.subtype} • {item.total_labs} Lab Draws
                      </div>
                    </div>
                  </div>

                  {/* Risk Badge */}
                  <div className="flex items-center space-x-2 shrink-0">
                    <div
                      className={`px-2.5 py-1 rounded-lg font-mono text-xs font-bold flex items-center gap-1.5 ${
                        isAlert
                          ? "bg-rose-600 text-white shadow-sm shadow-rose-600/30"
                          : isWatch
                          ? "bg-amber-950 text-amber-300 border border-amber-800"
                          : "bg-emerald-950 text-emerald-300 border border-emerald-800"
                      }`}
                    >
                      {isAlert && <AlertTriangle className="w-3 h-3 animate-pulse" />}
                      {(item.latest_risk * 100).toFixed(1)}%
                    </div>

                    <ChevronRight
                      className={`w-4 h-4 transition-transform ${
                        isSelected ? "text-cyan-400 translate-x-0.5" : "text-slate-600 group-hover:text-slate-400"
                      }`}
                    />
                  </div>
                </div>

                {/* Snippet of latest justification if alert */}
                {isAlert && (
                  <div className="mt-2 text-[11px] text-rose-300/90 font-medium bg-rose-950/40 p-2 rounded-lg border border-rose-900/40 line-clamp-2">
                    {item.latest_justification}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="text-[11px] text-slate-500 text-center pt-2 border-t border-slate-800/80 font-mono">
        Roster dynamically prioritized: highest predicted risk at top.
      </div>
    </div>
  );
};
