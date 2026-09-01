"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "@/lib/i18n/context";

/**
 * Progress while a search runs.
 *
 * HONESTY PROBLEM THIS HAD TO SOLVE: the backend streams nothing, so
 * there is no real completion figure to report. A bar that claims
 * "63%" would be inventing a measurement -- exactly what this project
 * forbids everywhere else.
 *
 * So the bar is explicitly a TIME estimate, not a progress reading: it
 * advances against the search's measured typical duration, is labelled
 * as an estimate, and never reaches 100% on its own -- it eases toward
 * a ceiling and waits there until the real results land. A bar that
 * sits full while nothing happens is worse than no bar.
 *
 * The stages ARE real: they name the work the backend does in order
 * (shortlist resorts, price flights, price beds, rank), taken from the
 * search pipeline itself.
 */

// Measured end-to-end search time, 2026-08: roughly 76-80s.
const TYPICAL_SECONDS = 78;
// Never claim more than this without real results -- the last stretch
// is where a slow provider actually shows up.
const CEILING = 94;
const TICK_MS = 250;

const STAGES = [
  { until: 12, key: "searchStageShortlist" },
  { until: 45, key: "searchStageFlights" },
  { until: 72, key: "searchStageStays" },
  { until: CEILING, key: "searchStageRanking" },
] as const;

export function SearchProgress({ done = false }: { done?: boolean }) {
  const { t } = useTranslation();
  const [pct, setPct] = useState(0);

  useEffect(() => {
    if (done) { setPct(100); return; }
    const started = Date.now();
    const id = window.setInterval(() => {
      const elapsed = (Date.now() - started) / 1000;
      // Ease out: quick at first, asymptotic near the ceiling, so an
      // overrunning search slows down rather than lying.
      const raw = 1 - Math.exp(-elapsed / (TYPICAL_SECONDS / 2.2));
      setPct(Math.min(CEILING, Math.round(raw * CEILING)));
    }, TICK_MS);
    return () => window.clearInterval(id);
  }, [done]);

  const stage = STAGES.find((s) => pct < s.until) ?? STAGES[STAGES.length - 1];

  return (
    <div className="mx-auto mt-6 max-w-xl" role="status" aria-live="polite">
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <span className="text-sm font-semibold text-ink">{t(stage.key)}</span>
        <span className="text-sm font-bold tabular-nums text-signal">{pct}%</span>
      </div>

      <div className="relative h-3 w-full overflow-hidden rounded-full bg-sunken">
        <div
          className="h-full rounded-full bg-signal transition-[width] duration-300 ease-out"
          style={{ width: `${pct}%` }}
        />
        {/* The skier rides the end of the bar. Decorative, so hidden
            from assistive tech -- the percentage above is the reading. */}
        <span
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 -translate-y-1/2 text-base transition-[left] duration-300 ease-out motion-reduce:transition-none"
          style={{ left: `calc(${pct}% - 10px)` }}
        >
          ⛷️
        </span>
      </div>

      {/* Said out loud: this is a clock, not a completion reading. */}
      <p className="mt-2 text-[11px] leading-snug text-subtle">{t("searchProgressNote")}</p>
    </div>
  );
}
