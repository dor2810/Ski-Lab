"use client";

import { useTranslation } from "@/lib/i18n/context";
import { LANGUAGES } from "@/lib/i18n/languages";

/**
 * Generic by construction: renders one button per entry in
 * lib/i18n/languages.ts's LANGUAGES array. Adding a third language
 * makes a third button appear here automatically -- nothing in this
 * file names "English" or "Hebrew" specifically.
 */
export function LanguageSwitcher() {
  const { code, setLanguageCode, t } = useTranslation();

  return (
    <div
      className="inline-flex gap-1 rounded-lg bg-midnight/80 p-1 backdrop-blur-sm border border-white/10"
      role="group"
      aria-label={t("languageLabel")}
    >
      {LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          type="button"
          onClick={() => setLanguageCode(lang.code)}
          aria-pressed={lang.code === code}
          className={`rounded-md px-2.5 py-1 text-xs font-semibold transition-colors ${
            lang.code === code ? "bg-signal text-white" : "text-ice/60 hover:text-white"
          }`}
        >
          {lang.nativeName}
        </button>
      ))}
    </div>
  );
}
