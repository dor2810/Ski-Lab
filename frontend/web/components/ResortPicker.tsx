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
  isSignedIn = true,
  showingAll = false,
  onToggleShowAll,
  hiddenCount = 0,
}: {
  resortNames: string[];
  selected: Set<string>;
  onToggle: (name: string) => void;
  mode: ResortFilterMode;
  onModeChange: (mode: ResortFilterMode) => void;
  // The resort list comes from an authenticated endpoint. Without this,
  // a signed-out visitor sat forever on "Loading resorts…" for a list
  // that was never going to arrive -- a small lie that reads as a
  // broken page, which is exactly the kind of thing that makes an
  // unsure user give up.
  isSignedIn?: boolean;
  // The picker defaults to a curated shortlist of resorts real ski
  // operators actually sell (see data/mainstream_resorts.py). The
  // toggle must stay VISIBLE rather than being a hidden default:
  // silently omitting resorts a user knows exist reads as a missing
  // feature, whereas an explicit "showing 31, show all 37" reads as
  // curation and stays trustworthy.
  showingAll?: boolean;
  onToggleShowAll?: () => void;
  hiddenCount?: number;
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
        <p className="text-xs font-semibold uppercase tracking-wide text-subtle">{t("resortsLabel")}</p>
        {selected.size > 0 && (
          <div className="flex gap-1 rounded-lg bg-canvas p-0.5">
            <button
              type="button"
              onClick={() => onModeChange("include")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "include" ? "bg-signal text-ink" : "text-subtle hover:text-ink"
              }`}
            >
              {t("resortsOnlyThese")}
            </button>
            <button
              type="button"
              onClick={() => onModeChange("exclude")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "exclude" ? "bg-signal text-ink" : "text-subtle hover:text-ink"
              }`}
            >
              {t("resortsExceptThese")}
            </button>
          </div>
        )}
      </div>

      {selected.size === 0 && (
        <p className="mb-2 text-[11px] text-subtle">
          {showingAll ? t("resortsNoneSelectedHintAll") : t("resortsNoneSelectedHintPopular")}
        </p>
      )}

      {onToggleShowAll && hiddenCount > 0 && (
        <button
          type="button"
          onClick={onToggleShowAll}
          className="mb-2 text-[11px] font-semibold text-sky hover:text-sky/80"
        >
          {showingAll
            ? t("resortsShowPopular")
            : t("resortsShowAll", { count: String(hiddenCount) })}
        </button>
      )}

      <input
        type="text"
        placeholder={t("resortsFilterPlaceholder")}
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-2 w-full rounded-lg border border-line bg-canvas px-3 py-2 text-sm text-ink outline-none focus:border-sky focus:ring-1 focus:ring-sky"
      />

      <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-line p-2">
        {resortNames.length === 0 && (
          <span className="text-xs text-subtle">
            {isSignedIn ? t("resortsLoading") : t("resortsSignInFirst")}
          </span>
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
                    ? "border-warn/50 bg-warn-soft text-warn"
                    : "border-sky bg-sky/15 text-sky"
                  : "border-line text-subtle hover:border-line-strong"
              }`}
            >
              {name}
            </button>
          );
        })}
        {visible.length === 0 && resortNames.length > 0 && (
          <span className="text-xs text-subtle">{t("resortsNoMatch", { filter })}</span>
        )}
      </div>
    </div>
  );
}
