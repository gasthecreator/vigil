"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTranslation, SupportedLocale, translations } from "@vigil/ui";
import { SyntheticBanner } from "@vigil/ui";
import { flushOfflineSyncQueue, getOfflineQueue } from "@/lib/api";
import { Shield, Globe, Wifi, WifiOff, RefreshCw } from "lucide-react";

export const Header: React.FC = () => {
  const { locale, setLocale, t } = useTranslation();
  const [offlineCount, setOfflineCount] = useState<number>(() => getOfflineQueue().length);
  const [isSyncing, setIsSyncing] = useState<boolean>(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  const handleSyncReplay = async () => {
    setIsSyncing(true);
    setSyncMessage(null);
    try {
      const res = await flushOfflineSyncQueue();
      if (res) {
        setSyncMessage(`Replayed ${res.applied_count} offline mutation(s) successfully.`);
      }
      setOfflineCount(getOfflineQueue().length);
    } catch {
      setSyncMessage("Offline sync failed. Check server connectivity.");
    } finally {
      setIsSyncing(false);
    }
  };

  const locales: { code: SupportedLocale; name: string; isReviewed: boolean }[] = [
    { code: "en-NG", name: "English (Nigeria)", isReviewed: true },
    { code: "pcm", name: "Naijá Pidgin [Unreviewed]", isReviewed: false },
    { code: "yo", name: "Èdè Yorùbá [Unreviewed]", isReviewed: false },
    { code: "ha", name: "Harshen Hausa [Unreviewed]", isReviewed: false },
    { code: "ig", name: "Asụsụ Igbo [Unreviewed]", isReviewed: false },
  ];

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-sm">
      {/* Prominent Synthetic Data Banner */}
      <SyntheticBanner isSynthetic={true} />

      {/* Unreviewed Translation Notice */}
      {t.common.unreviewedTranslationWarning && (
        <div className="bg-amber-400 text-amber-950 font-bold px-4 py-1 text-center text-xs flex items-center justify-center gap-2 border-b border-amber-500">
          <span>{t.common.unreviewedTranslationWarning}</span>
        </div>
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-emerald-700 flex items-center justify-center text-white shadow-sm">
            <Shield className="w-6 h-6" aria-hidden="true" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
              VIGIL
              <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                Clinician Workstation M9
              </span>
            </h1>
            <p className="text-xs text-slate-500">{t.common.appName}</p>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex items-center gap-2" aria-label="Main Navigation">
          <Link
            href="/"
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg text-slate-700 hover:bg-slate-100 transition-colors"
          >
            Clinician Workstation
          </Link>
          <Link
            href="/continuity"
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-indigo-50 text-indigo-800 border border-indigo-200 hover:bg-indigo-100 transition-colors"
          >
            RT Continuity (M7)
          </Link>
          <Link
            href="/companion"
            className="text-xs font-semibold px-2.5 py-1.5 rounded-lg bg-teal-50 text-teal-800 border border-teal-200 hover:bg-teal-100 transition-colors"
          >
            Family Companion
          </Link>
        </nav>

        {/* Controls: Offline Queue & Language Selector */}
        <div className="flex items-center gap-3">
          {/* Offline Sync Status & Button */}
          {offlineCount > 0 && (
            <div className="flex items-center gap-2 bg-amber-50 border border-amber-300 text-amber-900 px-3 py-1.5 rounded-lg text-xs font-medium">
              <WifiOff className="w-4 h-4 text-amber-700" />
              <span>{offlineCount} queued offline</span>
              <button
                onClick={handleSyncReplay}
                disabled={isSyncing}
                className="ml-2 underline font-bold hover:text-amber-950 flex items-center gap-1"
                aria-label="Sync offline mutations"
              >
                <RefreshCw className={`w-3 h-3 ${isSyncing ? "animate-spin" : ""}`} />
                Sync Now
              </button>
            </div>
          )}

          {syncMessage && (
            <span className="text-xs font-medium text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded border border-emerald-200">
              {syncMessage}
            </span>
          )}

          {/* Language Selector */}
          <div className="flex items-center gap-2 bg-slate-50 border border-slate-300 rounded-lg px-2.5 py-1.5 text-xs text-slate-700">
            <Globe className="w-4 h-4 text-slate-500" aria-hidden="true" />
            <label htmlFor="locale-selector" className="sr-only">
              Select Language
            </label>
            <select
              id="locale-selector"
              value={locale}
              onChange={(e) => setLocale(e.target.value as SupportedLocale)}
              className="bg-transparent font-medium text-slate-800 focus:outline-none cursor-pointer"
            >
              {locales.map((loc) => (
                <option key={loc.code} value={loc.code}>
                  {loc.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>
    </header>
  );
};
