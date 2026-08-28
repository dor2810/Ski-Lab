"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { AccommodationOption } from "@/lib/api";
import { StayIcon } from "./icons";

/**
 * The real, named properties behind a result's accommodation price --
 * mirror of FlightOptions, same reasoning: the scrape always returned
 * ~20 named, priced properties and we showed ONE name off it.
 *
 * Cheapest first with NO "best" badge, deliberately: the provider's
 * rating/distance fields aren't parsed (verified live -- they come
 * back null), so price is the only axis we can honestly rank on.
 * Inventing a "best hotel" from data we don't have is exactly what
 * this project forbids.
 *
 * Layout follows FlightOptions' two-line lesson: name on its own line
 * (property names run long -- "Chamonix Sud - Balme 102 - Happy
 * Rentals"), numbers on the line below, so a 390px phone never
 * scrolls sideways.
 */
export function AccommodationOptions({ options }: { options: AccommodationOption[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!options || options.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-line bg-sunken/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-sky hover:text-sky/80"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <StayIcon size={14} className="flex-none" />
          <span className="truncate">{t("accommodationOptionsTitle", { count: String(options.length) })}</span>
        </span>
        <span aria-hidden="true" className="text-xs text-subtle">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <>
          <ul className="mt-2.5 space-y-1.5">
            {options.map((o, i) => (
              <li
                key={`${o.property_name}-${i}`}
                className={`rounded-lg px-2 py-1.5 ${o.is_cheapest ? "bg-signal-soft" : ""}`}
              >
                <div className="flex min-w-0 items-baseline gap-2 text-xs">
                  <span className="min-w-0 flex-1 truncate font-semibold text-ink">
                    {o.property_name}
                  </span>
                  <span className="flex-none tabular-nums text-muted">
                    {t("accommodationPerNight", { price: String(Math.round(o.price_eur_per_night)) })}
                  </span>
                </div>
                <div className="mt-0.5 flex min-w-0 items-baseline gap-2 text-[11px] text-subtle">
                  <span className="min-w-0 flex-1 truncate">
                    {t("accommodationPerPersonStay", { price: String(Math.round(o.per_person_eur)) })}
                  </span>
                  <span className="flex-none tabular-nums">
                    {t("flightTripTotal", { total: String(Math.round(o.trip_total_eur)) })}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          {/* Price-only ordering, said out loud rather than implied. */}
          <p className="mt-2 text-[10px] leading-snug text-subtle">{t("accommodationOptionsNote")}</p>
        </>
      )}
    </div>
  );
}
