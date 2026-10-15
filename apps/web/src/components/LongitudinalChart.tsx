"use client";

import React, { useState } from "react";
import {
  ResponsiveContainer,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
  Area,
  ComposedChart,
} from "recharts";
import { TrajectoryPoint } from "@/lib/types";
import {
  Activity,
  AlertCircle,
  TrendingUp,
  Layers,
  Printer,
  Table,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
} from "lucide-react";
import { ClinicalAlertBanner } from "./ClinicalAlertBanner";

interface LongitudinalChartProps {
  trajectory: TrajectoryPoint[];
  patientId: string;
}

export const LongitudinalChart: React.FC<LongitudinalChartProps> = ({
  trajectory,
  patientId,
}) => {
  const [overlayMetric, setOverlayMetric] = useState<"none" | "ca_15_3" | "alt_level">("ca_15_3");
  const [showTable, setShowTable] = useState<boolean>(true);

  if (!trajectory || trajectory.length === 0) {
    return (
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-12 text-center space-y-3">
        <Activity className="w-12 h-12 text-slate-600 mx-auto animate-pulse" />
        <h3 className="text-base font-semibold text-slate-300">No Longitudinal Data</h3>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          Submit the first routine surveillance lab draw using the intake panel to initiate the
          attention-gated sequence model trajectory.
        </p>
      </div>
    );
  }

  // Format data for Recharts
  const chartData = trajectory.map((point) => {
    const d = new Date(point.date_drawn);
    const dateFormatted = d.toLocaleDateString("en-US", { month: "short", year: "numeric", day: "numeric" });
    return {
      dateStr: dateFormatted,
      timestamp: d.getTime(),
      risk: point.calculated_metastasis_risk,
      ci_lower: point.ci_lower ?? Math.max(0, point.calculated_metastasis_risk - 0.05),
      ci_upper: point.ci_upper ?? Math.min(1, point.calculated_metastasis_risk + 0.05),
      riskPct: Math.round(point.calculated_metastasis_risk * 100),
      ca_15_3: point.ca_15_3,
      alt_level: point.alt_level,
      ast_level: point.ast_level,
      creatinine: point.creatinine,
      wbc_count: point.wbc_count,
      ca_vel: point.ca153_velocity_pct ?? 0,
      alt_vel: point.alt_velocity_pct ?? 0,
      isAlert: point.calculated_metastasis_risk >= 0.75,
      justification: point.justification_text,
    };
  });

  const latestPoint = trajectory[trajectory.length - 1];
  const hasTriggeredAlert = latestPoint.calculated_metastasis_risk >= 0.75;

  const handlePrintDossier = () => {
    window.print();
  };

  return (
    <div className="space-y-4">
      {/* Actionable Second-Opinion Alert Banner if risk >= 0.75 */}
      {hasTriggeredAlert && (
        <ClinicalAlertBanner
          riskScore={latestPoint.calculated_metastasis_risk}
          justificationText={latestPoint.justification_text}
          patientId={patientId}
        />
      )}

      {/* Chart Card */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
        {/* Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-cyan-400" />
              <h2 className="text-base font-bold text-white tracking-wide">
                Longitudinal Metastasis Risk Trajectory
              </h2>
            </div>
            <p className="text-xs text-slate-400">
              PyTorch Attention-LSTM dynamic inference with conformal uncertainty band and velocity tracking.
            </p>
          </div>

          <div className="flex items-center space-x-2 text-xs flex-wrap">
            {/* Overlay Biomarker Controls */}
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800">
              <button
                onClick={() => setOverlayMetric("none")}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  overlayMetric === "none"
                    ? "bg-slate-800 text-cyan-300 font-semibold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                None
              </button>
              <button
                onClick={() => setOverlayMetric("ca_15_3")}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  overlayMetric === "ca_15_3"
                    ? "bg-amber-950/80 text-amber-300 border border-amber-800/60 font-semibold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                CA 15-3 Overlay
              </button>
              <button
                onClick={() => setOverlayMetric("alt_level")}
                className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                  overlayMetric === "alt_level"
                    ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800/60 font-semibold"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                ALT Overlay
              </button>
            </div>

            {/* Print Dossier */}
            <button
              onClick={handlePrintDossier}
              className="p-1.5 rounded-lg bg-slate-950 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 transition-colors"
              title="Print Clinical Dossier"
            >
              <Printer className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Recharts Trajectory Plot */}
        <div className="h-80 w-full pt-2">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 15, right: 25, left: -10, bottom: 5 }}>
              <defs>
                <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                </linearGradient>
                <linearGradient id="ciGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0284c7" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#0284c7" stopOpacity={0.05} />
                </linearGradient>
              </defs>

              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />

              <XAxis
                dataKey="dateStr"
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                tickLine={{ stroke: "#334155" }}
              />

              {/* Primary Y-Axis: Metastasis Risk (0.0 - 1.0) */}
              <YAxis
                yAxisId="riskAxis"
                domain={[0.0, 1.0]}
                ticks={[0.0, 0.25, 0.5, 0.75, 1.0]}
                tickFormatter={(val) => `${Math.round(val * 100)}%`}
                stroke="#64748b"
                tick={{ fill: "#94a3b8", fontSize: 11 }}
                tickLine={{ stroke: "#334155" }}
              />

              {/* Optional Secondary Y-Axis for Overlay Biomarker */}
              {overlayMetric !== "none" && (
                <YAxis
                  yAxisId="bioAxis"
                  orientation="right"
                  stroke={overlayMetric === "ca_15_3" ? "#f59e0b" : "#10b981"}
                  tick={{ fill: overlayMetric === "ca_15_3" ? "#f59e0b" : "#10b981", fontSize: 11 }}
                  tickFormatter={(val) => `${val}`}
                />
              )}

              {/* Clinical Alert Threshold Reference Line at y = 0.75 */}
              <ReferenceLine
                yAxisId="riskAxis"
                y={0.75}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: "Clinical Alert Threshold (0.75)",
                  fill: "#f87171",
                  fontSize: 11,
                  position: "top",
                }}
              />

              {/* Tooltip */}
              <Tooltip content={<CustomTooltip />} />

              {/* Conformal Uncertainty Ribbon Upper */}
              <Area
                yAxisId="riskAxis"
                type="monotone"
                dataKey="ci_upper"
                stroke="none"
                fill="url(#ciGradient)"
                name="Confidence Ribbon"
              />

              {/* Risk Curve Area */}
              <Area
                yAxisId="riskAxis"
                type="monotone"
                dataKey="risk"
                stroke="#06b6d4"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#riskGradient)"
                dot={(props: any) => {
                  const { cx, cy, payload } = props;
                  const isCritical = payload.risk >= 0.75;
                  return (
                    <circle
                      key={props.key || `${cx}-${cy}`}
                      cx={cx}
                      cy={cy}
                      r={isCritical ? 7 : 5}
                      fill={isCritical ? "#ef4444" : "#06b6d4"}
                      stroke="#0f172a"
                      strokeWidth={2}
                      className={isCritical ? "animate-pulse" : ""}
                    />
                  );
                }}
              />

              {/* Overlay Line for CA 15-3 */}
              {overlayMetric === "ca_15_3" && (
                <Line
                  yAxisId="bioAxis"
                  type="monotone"
                  dataKey="ca_15_3"
                  stroke="#f59e0b"
                  strokeWidth={2}
                  strokeDasharray="2 2"
                  dot={{ r: 3, fill: "#f59e0b" }}
                  name="CA 15-3 (U/mL)"
                />
              )}

              {/* Overlay Line for ALT */}
              {overlayMetric === "alt_level" && (
                <Line
                  yAxisId="bioAxis"
                  type="monotone"
                  dataKey="alt_level"
                  stroke="#10b981"
                  strokeWidth={2}
                  strokeDasharray="2 2"
                  dot={{ r: 3, fill: "#10b981" }}
                  name="ALT (U/L)"
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* Legend / Status Footnote */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 pt-1">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-full bg-cyan-500 inline-block"></span>
              Metastatic Risk Curve
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-0.5 w-4 bg-rose-500 border-t border-dashed border-rose-500 inline-block"></span>
              Alert Cutoff (0.75)
            </span>
            <span className="flex items-center gap-1.5 text-sky-400">
              <span className="h-2.5 w-4 bg-sky-900/60 rounded inline-block border border-sky-600/50"></span>
              90% Conformal Band
            </span>
          </div>

          <button
            onClick={() => setShowTable(!showTable)}
            className="flex items-center gap-1 text-slate-300 hover:text-cyan-400 transition-colors font-medium"
          >
            <Table className="w-3.5 h-3.5" />
            {showTable ? "Hide Velocity Matrix" : "Show Velocity Matrix"}
          </button>
        </div>

        {/* Biomarker Velocity & Trajectory Matrix Table */}
        {showTable && (
          <div className="overflow-x-auto pt-2 border-t border-slate-800/80">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px] tracking-wider">
                  <th className="py-2 px-3">Date Drawn</th>
                  <th className="py-2 px-3">CA 15-3 (Tumor)</th>
                  <th className="py-2 px-3">ALT (Liver)</th>
                  <th className="py-2 px-3">AST</th>
                  <th className="py-2 px-3">De Ritis (AST/ALT)</th>
                  <th className="py-2 px-3">WBC</th>
                  <th className="py-2 px-3">Creatinine</th>
                  <th className="py-2 px-3 text-right">Risk Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {chartData.map((row, idx) => {
                  const deRitis = (row.ast_level / Math.max(row.alt_level, 1)).toFixed(2);
                  return (
                    <tr
                      key={idx}
                      className={row.isAlert ? "bg-rose-950/20 text-rose-200" : "hover:bg-slate-950/40 text-slate-300"}
                    >
                      <td className="py-2 px-3 font-semibold text-slate-200">{row.dateStr}</td>
                      <td className="py-2 px-3">
                        <span className="font-bold text-amber-300">{row.ca_15_3}</span> U/mL
                        {row.ca_vel !== 0 && (
                          <span
                            className={`ml-1.5 text-[10px] px-1 py-0.2 rounded font-sans inline-flex items-center ${
                              row.ca_vel > 0 ? "text-rose-400 bg-rose-950/60" : "text-emerald-400 bg-emerald-950/60"
                            }`}
                          >
                            {row.ca_vel > 0 ? <ArrowUpRight className="w-2.5 h-2.5" /> : <ArrowDownRight className="w-2.5 h-2.5" />}
                            {row.ca_vel > 0 ? "+" : ""}{row.ca_vel}%
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3">
                        <span className={row.alt_level > 40 ? "font-bold text-rose-300" : ""}>{row.alt_level}</span> U/L
                        {row.alt_vel !== 0 && (
                          <span
                            className={`ml-1.5 text-[10px] px-1 py-0.2 rounded font-sans inline-flex items-center ${
                              row.alt_vel > 0 ? "text-rose-400 bg-rose-950/60" : "text-emerald-400 bg-emerald-950/60"
                            }`}
                          >
                            {row.alt_vel > 0 ? <ArrowUpRight className="w-2.5 h-2.5" /> : <ArrowDownRight className="w-2.5 h-2.5" />}
                            {row.alt_vel > 0 ? "+" : ""}{row.alt_vel}%
                          </span>
                        )}
                      </td>
                      <td className="py-2 px-3">{row.ast_level} U/L</td>
                      <td className="py-2 px-3">{deRitis}</td>
                      <td className="py-2 px-3">{row.wbc_count}</td>
                      <td className="py-2 px-3">{row.creatinine}</td>
                      <td className="py-2 px-3 text-right">
                        <span
                          className={`px-2 py-0.5 rounded font-bold ${
                            row.isAlert
                              ? "bg-rose-600 text-white"
                              : row.risk >= 0.4
                              ? "bg-amber-950 text-amber-300 border border-amber-800"
                              : "bg-emerald-950 text-emerald-300"
                          }`}
                        >
                          {(row.risk * 100).toFixed(1)}%
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

function CustomTooltip({ active, payload, label }: any) {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const isAlert = data.risk >= 0.75;
    return (
      <div className="bg-slate-950 border border-slate-700/80 rounded-xl p-3.5 shadow-2xl space-y-2 text-xs max-w-xs">
        <div className="flex justify-between items-center border-b border-slate-800 pb-1.5">
          <span className="font-bold text-slate-200">{data.dateStr}</span>
          <span
            className={`font-mono font-bold px-2 py-0.5 rounded text-[11px] ${
              isAlert
                ? "bg-rose-950 text-rose-300 border border-rose-800"
                : "bg-cyan-950 text-cyan-300 border border-cyan-800"
            }`}
          >
            Risk: {(data.risk * 100).toFixed(1)}%
          </span>
        </div>

        <div className="grid grid-cols-2 gap-2 text-slate-300 font-mono text-[11px]">
          <div>CA 15-3: <strong className="text-white">{data.ca_15_3}</strong> U/mL</div>
          <div>ALT: <strong className="text-white">{data.alt_level}</strong> U/L</div>
          <div>AST: <strong className="text-white">{data.ast_level}</strong> U/L</div>
          <div>WBC: <strong className="text-white">{data.wbc_count}</strong> x10^9</div>
          <div>Creatinine: <strong className="text-white">{data.creatinine}</strong> mg/dL</div>
        </div>

        <div className="pt-1 text-[10px] text-slate-400 font-mono">
          90% Conformal Range: [{(data.ci_lower * 100).toFixed(0)}% - {(data.ci_upper * 100).toFixed(0)}%]
        </div>

        {isAlert && (
          <div className="text-[11px] text-rose-300 bg-rose-950/60 p-1.5 rounded border border-rose-900 leading-tight">
            🚨 Threshold Exceeded: Actionable Second-Opinion Recommended
          </div>
        )}
      </div>
    );
  }
  return null;
}
