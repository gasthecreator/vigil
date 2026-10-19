"use client";

/**
 * packages/ui/src/i18n/index.ts
 *
 * Multilingual context and hook for Vigil Clinician Workstation.
 */

import React, { createContext, useContext, useState, useEffect } from "react";
import { SupportedLocale, TranslationDictionary } from "./types";
import { enNG } from "./translations/en-NG";
import { pcm } from "./translations/pcm";
import { yo } from "./translations/yo";
import { ha } from "./translations/ha";
import { ig } from "./translations/ig";

export * from "./types";

export const translations: Record<SupportedLocale, TranslationDictionary> = {
  "en-NG": enNG,
  pcm,
  yo,
  ha,
  ig,
};

interface I18nContextValue {
  locale: SupportedLocale;
  direction: "ltr" | "rtl";
  setLocale: (locale: SupportedLocale) => void;
  t: TranslationDictionary;
  isReviewed: boolean;
  unreviewedNotice?: string;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "en-NG",
  direction: "ltr",
  setLocale: () => {},
  t: enNG,
  isReviewed: true,
});

export const I18nProvider: React.FC<{
  initialLocale?: SupportedLocale;
  direction?: "ltr" | "rtl";
  children: React.ReactNode;
}> = ({ initialLocale = "en-NG", direction = "ltr", children }) => {
  const [locale, setLocaleState] = useState<SupportedLocale>(initialLocale);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("vigil_locale") as SupportedLocale;
      if (saved && translations[saved]) {
        setLocaleState(saved);
      }
    }
  }, []);

  const setLocale = (newLocale: SupportedLocale) => {
    setLocaleState(newLocale);
    if (typeof window !== "undefined") {
      localStorage.setItem("vigil_locale", newLocale);
    }
  };

  const currentDict = translations[locale] || enNG;

  return (
    <I18nContext.Provider
      value={{
        locale,
        direction,
        setLocale,
        t: currentDict,
        isReviewed: currentDict.metadata.isReviewed,
        unreviewedNotice: currentDict.metadata.unreviewedNotice,
      }}
    >
      <div dir={direction} lang={locale} className="contents">{children}</div>
    </I18nContext.Provider>
  );
};

export const useTranslation = (): I18nContextValue => useContext(I18nContext);
