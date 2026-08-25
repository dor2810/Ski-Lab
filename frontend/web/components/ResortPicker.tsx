"use client";

import { useState } from "react";

export type ResortFilterMode = "include" | "exclude";

/**
 * "Select or deselect specific resorts" -- lets a user pin the search
 * to 2-3 specific resorts ("Only these") or broadly exclude a few
 * ("All except these"), reusing the same multi-select chip list for
 * both -- only the interpretation (include vs exclude) toggles.
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
  const [filter, setFilter] = useState("");
  const visible = resortNames.filter((n) => n.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-wide text-ice/60">Resorts</p>
        {selected.size > 0 && (
          <div className="flex gap-1 rounded-lg bg-navy p-0.5">
            <button
              type="button"
              onClick={() => onModeChange("include")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "include" ? "bg-signal text-white" : "text-ice/50 hover:text-white"
              }`}
            >
              Only these
            </button>
            <button
              type="button"
              onClick={() => onModeChange("exclude")}
              className={`rounded-md px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                mode === "exclude" ? "bg-signal text-white" : "text-ice/50 hover:text-white"
              }`}
            >
              Except these
            </button>
          </div>
        )}
      </div>

      {selected.size === 0 && (
        <p className="mb-2 text-[11px] text-ice/40">
          None selected = search all resorts. Pick some to search only those, or flip to
          &ldquo;Except these&rdquo; to exclude them.
        </p>
      )}

      <input
        type="text"
        placeholder="Filter resorts…"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        className="mb-2 w-full rounded-lg border border-white/15 bg-navy px-3 py-2 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky"
      />

      <div className="flex max-h-40 flex-wrap gap-1.5 overflow-y-auto rounded-lg border border-white/10 p-2">
        {resortNames.length === 0 && (
          <span className="text-xs text-ice/40">Loading resorts…</span>
        )}
        {visible.map((name) => {
          const active = selected.has(name);
          return (
            <button
              type="button"
              key={name}
              onClick={() => onToggle(name)}
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
          <span className="text-xs text-ice/40">No resorts match &ldquo;{filter}&rdquo;.</span>
        )}
      </div>
    </div>
  );
}
