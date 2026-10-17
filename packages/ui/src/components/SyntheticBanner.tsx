"use client";

import React from "react";
import { AlertTriangle } from "lucide-react";
import { useTranslation } from "../i18n";

export interface SyntheticBannerProps {
  isSynthetic?: boolean;
}

export const SyntheticBanner: React.FC<SyntheticBannerProps> = ({ isSynthetic = true }) => {
  const { t, isReviewed, unreviewedNotice } = useTranslation();

  if (!isSynthetic) return null;

  return (
    <div className="w-full bg-amber-500 text-slate-950 px-4 py-2 text-xs font-bold border-b border-amber-600 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-2 z-50">
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 text-slate-950 flex-shrink-0" aria-hidden="true" />
        <span>
          <span className="uppercase tracking-wider mr-2 font-black">[{t.common.syntheticBanner}]</span>
          {t.common.syntheticDescription}
        </span>
      </div>
      {!isReviewed && unreviewedNotice && (
        <div className="text-[11px] bg-amber-200 text-amber-950 px-2 py-0.5 rounded border border-amber-400 font-semibold">
          {unreviewedNotice}
        </div>
      )}
    </div>
  );
};
