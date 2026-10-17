"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslation, SupportedLocale, Badge } from "@vigil/ui";
import {
  Heart,
  Activity,
  Share2,
  AlertOctagon,
  Globe,
  Wifi,
  WifiOff,
  ShieldAlert,
} from "lucide-react";

export default function CompanionLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { t, locale, setLocale, isReviewed, unreviewedNotice } = useTranslation();
  const pathname = usePathname();
  const [isOnline, setIsOnline] = useState<boolean>(true);

  React.useEffect(() => {
    setIsOnline(navigator.onLine);
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const navItems = [
    { href: "/companion", label: "Dashboard", icon: Heart },
    { href: "/companion/symptoms", label: "Symptoms", icon: Activity },
    { href: "/companion/share", label: "Caregivers", icon: Share2 },
  ];

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans pb-20 md:pb-6">
      {/* 1. Mandatory Urgent-Symptom Notice (Master Plan §11.1) */}
      <div
        className="bg-rose-700 text-white px-4 py-2 text-xs md:text-sm font-medium flex items-center justify-between"
        role="alert"
        aria-live="polite"
      >
        <div className="max-w-4xl mx-auto flex items-center gap-2">
          <AlertOctagon className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{t.companion.emergencyNotice}</span>
        </div>
      </div>

      {/* 2. Synthetic Data Banner & Translation Review Marker */}
      <div className="bg-amber-500 text-amber-950 px-4 py-1.5 text-xs font-semibold flex items-center justify-between">
        <div className="max-w-4xl mx-auto w-full flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="uppercase tracking-wider">Research Prototype:</span>
            <span>{t.common.syntheticDescription}</span>
          </div>
          {!isReviewed && (
            <span className="bg-amber-600 text-white px-2 py-0.5 rounded text-[11px] font-bold">
              {unreviewedNotice || "Unreviewed Translation (Machine Draft)"}
            </span>
          )}
        </div>
      </div>

      {/* 3. Top Navigation & Language Switcher */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <Link href="/companion" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-teal-600 text-white flex items-center justify-center font-bold text-lg shadow-sm">
              V
            </div>
            <div>
              <span className="font-bold text-slate-900 text-base tracking-tight group-hover:text-teal-700 transition-colors">
                Vigil Companion
              </span>
              <span className="hidden sm:inline-block ml-2 text-xs text-slate-600 font-normal">
                Patient & Family Care
              </span>
            </div>
          </Link>

          <div className="flex items-center gap-3">
            {/* Online / Offline Indicator */}
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${
                isOnline ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"
              }`}
              title={isOnline ? "Online" : "Offline mode active"}
            >
              {isOnline ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-600" />
                  <span className="hidden sm:inline">Online</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-rose-600" />
                  <span>Offline</span>
                </>
              )}
            </div>

            {/* Language Picker */}
            <div className="flex items-center gap-1 text-slate-600 bg-slate-100 rounded-lg px-2 py-1">
              <Globe className="w-3.5 h-3.5 text-slate-500" aria-hidden="true" />
              <select
                value={locale}
                onChange={(e) => setLocale(e.target.value as SupportedLocale)}
                className="bg-transparent text-xs font-medium text-slate-700 focus:outline-none cursor-pointer"
                aria-label="Select language"
              >
                <option value="en-NG">English (NG)</option>
                <option value="pcm">Naijá Pidgin [Draft]</option>
                <option value="yo">Yorùbá [Draft]</option>
                <option value="ha">Hausa [Draft]</option>
                <option value="ig">Igbo [Draft]</option>
              </select>
            </div>
          </div>
        </div>
      </header>

      {/* 4. Main Body */}
      <div className="flex-1 max-w-4xl w-full mx-auto p-4 md:p-6">{children}</div>

      {/* 5. Mobile Bottom Tab Bar */}
      <nav
        className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 z-40 px-4 py-2 flex items-center justify-around shadow-lg"
        aria-label="Companion Navigation"
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex flex-col items-center gap-1 px-3 py-1 rounded-lg text-xs font-medium transition-colors ${
                isActive
                  ? "text-teal-700 font-bold"
                  : "text-slate-500 hover:text-slate-900"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className={`w-5 h-5 ${isActive ? "text-teal-600" : "text-slate-400"}`} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* 6. Footer Disclaimer */}
      <footer className="mt-8 border-t border-slate-200 bg-white py-4 px-4 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto space-y-1">
          <p>{t.companion.disclaimer}</p>
          <p className="text-slate-600">Vigil Platform Phase 6b • Family & Patient Companion (M8)</p>
        </div>
      </footer>
    </div>
  );
}
