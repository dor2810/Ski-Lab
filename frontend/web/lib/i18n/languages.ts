import en from "./en";
import he from "./he";

export type Dictionary = Record<keyof typeof en, string>;

export interface LanguageDef {
  code: string; // BCP-47-ish code, also used as the localStorage value and <html lang>
  nativeName: string; // shown in the switcher, in the language's OWN script (not translated)
  dir: "ltr" | "rtl";
  dictionary: Dictionary;
  locale: string; // full Intl locale for Number/Date formatting (thousands separators, month names)
}

/**
 * THE extension point: to add a language, write lib/i18n/xx.ts (copy
 * he.ts's shape -- TypeScript enforces every key exists), then add one
 * entry here. Nothing else in the app needs to change -- the switcher,
 * the provider, and every component's t() calls are all driven by this
 * list and the Dictionary type, not by hardcoded language checks.
 */
export const LANGUAGES: LanguageDef[] = [
  { code: "en", nativeName: "English", dir: "ltr", dictionary: en, locale: "en-GB" },
  { code: "he", nativeName: "עברית", dir: "rtl", dictionary: he, locale: "he-IL" },
];

export const DEFAULT_LANGUAGE_CODE = "en";

export function getLanguage(code: string): LanguageDef {
  return LANGUAGES.find((l) => l.code === code) ?? LANGUAGES[0];
}
