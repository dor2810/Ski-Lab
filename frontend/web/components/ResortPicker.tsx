"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";

export type ResortFilterMode = "include" | "exclude";

/**
 * "Select or deselect specific resorts" -- lets a user pin the search
 * to 2-3 specific resorts ("Only these") or broadly exclude a few
 * ("All except these"), reusing the same multi-select chip list for
 * both -- only the interpretation (include vs exclude) toggles.
 *
 * Resort NAMES themselves (Livigno, St. Anton am Arlberg, ...) are
 * deliberately not translated -- they come from the backend as-is (see
 * lib/api.ts), and are proper nouns without an authoritative Hebrew
 * form to draw from. Everything AROUND them (this component's own UI)
 * is translated.
 */
export function ResortPicker({
  resortNames,
  selected,
  onToggle,
  mode,
  onModeChange,
}: {
  resortNames: string[];
  selected: Set<string>;
  onToggle: (name: string) => void;
  mode: ResortFilterMode;
  onModeChange: (mode: ResortFilterMode) => void;
}) {
  const { t } = useTranslation();
  const [filter, setFilter] = useState("");

  // Selected resorts sort to the front (stable sort preserves each
  // group's original alphabetical order) -- picking a resort should
  // make it visibly, immediately part of "what you've chosen", not
  // leave it wherever it happened to fall alphabetically.
  const visible = resortNames
    .filter((n) => n.toLowerCase().includes(filter.toLowerCase()))
    .sort((a, b) => Number(selected.has(b)) - Number(selected.has(a)));

  // Clearing the filter after a click (not just on select) means
  // typing a name to find it, tapping it, and immediately seeing the
  // full list again with your pick now pinned at the front -- exactly
  // the point of searching for one resort at a time rather than
  // scrolling the whole list.
  function handleToggle(name: string) {
    onToggle(name);
    setFilter("");
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-ice/60">{t("resortsLabel")}</p>
        {selected.size > 0 && (
          <div className="flex gap-1 rounded-lg bg-navy p-0.5">
            <button
              type="button"
              onClick={() => onModeChange("include")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "include" ? "bg-signal text-white" : "text-ice/50 hover:text-white"
              }`}
            >
              {t("resortsOnlyThese")}
            </button>
            <button
              type="button"
              onClick={() => onModeChange("exclude")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "exclude" ? "bg-signal text-white" : "text-ice/50 hover:text-white"
              }`}
            >
              {t("resortsExceptThese")}
            </button>
          </div>
        )}
      </div>

      {selected.size === 0 && (
        <p className="mb-2 text-[11px] text-ice/40">{t("resortsNoneSelectedHint")}</p>
      )}

      <input
        type="text"
        placeholder={t("resortsFilterPlaceholder")}
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-2 w-full rounded-lg border border-white/15 bg-navy px-3 py-2 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky"
      />

      <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-white/10 p-2">
        {resortNames.length === 0 && (
          <span className="text-xs text-ice/40">{t("resortsLoading")}</span>
        )}
        {visible.map((name) => {
          const active = selected.has(name);
          return (
            <button
              type="button"
              key={name}
              onClick={() => handleToggle(name)}
              aria-pressed={active}
              className={`rounded-full border px-2.5 py-1 text-xs font-medium transition-colors ${
                active
                  ? mode === "exclude"
                    ? "border-red-400/50 bg-red-500/15 text-red-300"
                    : "border-sky bg-sky/15 text-sky"
                  : "border-white/15 text-ice/60 hover:border-white/30"
              }`}
            >
              {name}
            </button>
          );
        })}
        {visible.length === 0 && resortNames.length > 0 && (
          <span className="text-xs text-ice/40">{t("resortsNoMatch", { filter })}</span>
        )}
      </div>
    </div>
  );
}
