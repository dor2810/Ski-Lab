"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { FlightOption } from "@/lib/api";
import { FlightIcon } from "./icons";

/**
 * The real itineraries behind a result's flight price.
 *
 * WHY THIS EXISTS: the flight search always returned a LIST of priced
 * flights and we kept one number off it. On a real TLV->GVA search the
 * cheapest was EUR283 for a FOURTEEN AND A HALF HOUR journey, while
 * EUR392 got there in six hours and a nonstop was 3h35. Showing only
 * the EUR283 makes the trip total look great while silently assuming
 * the traveller will spend two full days getting there -- technically
 * true, and exactly the kind of misleading number this project exists
 * not to produce.
 *
 * The point is not "more data". It is that "cheapest" stops being a
 * hidden assumption and becomes a visible choice.
 */

// How much longer than the fastest option a flight has to be before it
// is worth warning about. Judgement, not a sourced figure: four hours
// is roughly the point where a stopover stops being an inconvenience
// and costs you a day of the trip.
const PUNISHING_EXTRA_MINUTES = 4 * 60;

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h${String(m).padStart(2, "0")}`;
}

export function FlightOptions({ options }: { options: FlightOption[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!options || options.length === 0) return null;

  const cheapest = options[0];
  const fastest = options.reduce((a, b) => (a.duration_minutes <= b.duration_minutes ? a : b));
  // Only worth flagging when a real, better-value alternative exists:
  // the cheapest is genuinely punishing AND something faster is here.
  const cheapestIsPunishing =
    cheapest.duration_minutes - fastest.duration_minutes >= PUNISHING_EXTRA_MINUTES;

  return (
    <div className="mt-3 rounded-xl border border-line bg-sunken/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-sky hover:text-sky/80"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <FlightIcon size={14} className="flex-none" />
          <span className="truncate">{t("flightOptionsTitle", { count: String(options.length) })}</span>
        </span>
        <span aria-hidden="true" className="text-xs text-subtle">{open ? "−" : "+"}</span>
      </button>

      {cheapestIsPunishing && (
        <p className="mt-1.5 text-[11px] leading-snug text-warn">
          {t("flightCheapestIsSlow", {
            cheapDuration: formatDuration(cheapest.duration_minutes),
            fastDuration: formatDuration(fastest.duration_minutes),
            extra: String(Math.round(fastest.price_eur - cheapest.price_eur)),
          })}
        </p>
      )}

      {open && (
        <ul className="mt-2.5 space-y-1.5">
          {options.map((o, i) => (
            <li
              key={`${o.airline}-${o.price_eur}-${i}`}
              className={`flex min-w-0 items-center gap-2 rounded-lg px-2 py-1.5 text-xs ${
                o.is_cheapest ? "bg-signal-soft" : ""
              }`}
            >
              <span className="w-14 flex-none font-semibold tabular-nums text-ink">
                €{Math.round(o.price_eur)}
              </span>
              <span className="min-w-0 flex-1 truncate text-muted">{o.airline}</span>
              <span className="flex-none tabular-nums text-muted">
                {formatDuration(o.duration_minutes)}
              </span>
              <span className="w-16 flex-none text-end text-subtle">
                {o.stops === 0
                  ? t("flightNonstop")
                  : o.stops === 1
                    ? t("flightOneStop")
                    : t("flightStops", { n: String(o.stops) })}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
