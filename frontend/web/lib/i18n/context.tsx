"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { LANGUAGES, DEFAULT_LANGUAGE_CODE, getLanguage, type Dictionary } from "./languages";

const STORAGE_KEY = "ski-lab-language";

interface LanguageContextValue {
  code: string;
  dir: "ltr" | "rtl";
  locale: string;
  /**
   * {param} tokens in the dictionary string are replaced by the matching
   * key in `params` -- e.g. t("kmPiste", {km: 150}) -> "150 km piste".
   * A hand-rolled replace() is enough here on purpose: this app has no
   * plural forms that vary by count (Hebrew and English both just show
   * a bare number) and no nested/rich formatting, so pulling in an ICU
   * message-format library would be solving a problem this app doesn't
   * have. Revisit if a future language actually needs real pluralization.
   */
  t: (key: keyof Dictionary, params?: Record<string, string | number>) => string;
  setLanguageCode: (code: string) => void;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Always starts at the default (English) so the FIRST client render
  // matches the static-exported HTML exactly (this is `output: "export"`
  // -- the HTML delivered to every visitor was built once, in English,
  // at build time) -- no hydration mismatch. A returning visitor's saved
  // language is applied a moment later, in the effect below, which is
  // why there's a brief flash back to English before switching to their
  // saved language on repeat visits, rather than an instant switch.
  // Proper per-language static routes would remove the flash entirely
  // but are a much bigger change than "add a language switcher" --
  // flagged here honestly rather than silently accepted as fine.
  const [code, setCode] = useState(DEFAULT_LANGUAGE_CODE);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved && LANGUAGES.some((l) => l.code === saved)) {
        setCode(saved);
      }
    } catch {
      /* localStorage can throw in private-browsing/storage-blocked contexts -- default stands */
    }
  }, []);

  const lang = getLanguage(code);

  useEffect(() => {
    document.documentElement.lang = lang.code;
    document.documentElement.dir = lang.dir;
  }, [lang.code, lang.dir]);

  function setLanguageCode(next: string) {
    setCode(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* non-fatal -- the choice still applies for this session via React state */
    }
  }

  function t(key: keyof Dictionary, params?: Record<string, string | number>): string {
    let value: string = lang.dictionary[key];
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        value = value.replace(new RegExp(`\\{${k}\\}`, "g"), String(v));
      }
    }
    return value;
  }

  return (
    <LanguageContext.Provider value={{ code: lang.code, dir: lang.dir, locale: lang.locale, t, setLanguageCode }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useTranslation() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useTranslation must be used within a LanguageProvider");
  return ctx;
}
