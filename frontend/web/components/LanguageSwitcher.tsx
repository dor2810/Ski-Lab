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
      className="inline-flex gap-1 rounded-lg bg-surface/80 p-1 backdrop-blur-sm border border-line"
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
            lang.code === code ? "bg-signal text-ink" : "text-subtle hover:text-ink"
          }`}
        >
          {lang.nativeName}
        </button>
      ))}
    </div>
  );
}
