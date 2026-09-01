"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { AccommodationOption } from "@/lib/api";
import { ExternalLinkIcon, StayIcon } from "./icons";
import { OptionRadioGroup, SelectableOptionRow } from "./SelectableOptionRow";

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
export function AccommodationOptions({
  options, selectedIndex = 0, onSelect, tripTotalFor, defaultOpen = false,
}: {
  options: AccommodationOption[];
  // The chosen property drives the accommodation line in the cost
  // breakdown and the card total, so this is a real selection.
  selectedIndex?: number;
  onSelect?: (index: number) => void;
  /** Whole-trip cost for a given per-person stay price, with the
   *  card's other selections held as they are. */
  tripTotalFor?: (stayEur: number) => number;
  /** Start expanded. Used inside the Trip details tabs, where the tab
   *  already IS the disclosure, so a second shut layer only costs a
   *  click. */
  defaultOpen?: boolean;
}) {
  const { t } = useTranslation();
  // Inside the Trip details tabs the tab IS the disclosure, so a
  // second collapsed layer just costs a click -- and clicking
  // "Flight" in the cost breakdown would land you on a shut panel.
  const [open, setOpen] = useState(defaultOpen);

  if (!options || options.length === 0) return null;

  return (
    <div className="mt-2 rounded-lg border border-line bg-surface px-3 py-2.5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-ink hover:text-signal"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <StayIcon size={14} className="flex-none" />
          <span className="truncate">{t("accommodationOptionsTitle", { count: String(options.length) })}</span>
        </span>
        <span aria-hidden="true" className="text-base leading-none text-subtle">{open ? "\u2212" : "+"}</span>
      </button>

      {open && (
        <>
          <OptionRadioGroup label={t("accommodationOptionsTitle", { count: String(options.length) })}>
            {options.map((o, i) => (
              <SelectableOptionRow
                key={`${o.property_name}-${i}`}
                selected={i === selectedIndex}
                onSelect={onSelect ? () => onSelect(i) : undefined}
                selectedLabel={t("accommodationSelected")}
                tint={o.is_cheapest ? "bg-sunken" : undefined}
              >
                <div className="flex min-w-0 items-baseline gap-2 text-xs">
                  {/* The name IS the link -- a separate button per row
                      needed width the phone doesn't have (see the
                      432px lesson in FlightOptions). Dated Google
                      Hotels search narrowed to this property.

                      It deliberately does NOT stretch: the row itself
                      is the select target now, so the empty space
                      beside a short property name has to belong to the
                      row, not to the link. */}
                  <span className="flex min-w-0 flex-1">
                    <a
                      href={o.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex min-w-0 items-center gap-1 font-semibold text-sky hover:underline"
                    >
                      <span className="min-w-0 truncate">{o.property_name}</span>
                      <ExternalLinkIcon size={11} className="flex-none opacity-70" />
                    </a>
                  </span>
                  <span className="flex-none tabular-nums text-muted">
                    {t("accommodationPerNight", { price: String(Math.round(o.price_eur_per_night)) })}
                  </span>
                </div>
                <div className="mt-0.5 flex min-w-0 items-baseline gap-2 text-[11px] text-subtle">
                  {/* Distance to the lifts leads the detail line: on a
                      ski trip it is the fact people actually choose on.
                      Shown in metres under 1km (a "0.05 km" walk reads
                      as noise), and only when genuinely known. */}
                  {o.distance_to_lifts_km != null && (
                    <span className="flex-none font-semibold text-sky">
                      {t("accommodationToLifts", {
                        m: String(Math.round(o.distance_to_lifts_km * 1000)),
                      })}
                    </span>
                  )}
                  {/* Star class is the property's own classification;
                      the rating beside it is what guests scored it.
                      Two different claims, so they are never merged --
                      and a property Google has not classified simply
                      shows no stars rather than being marked down. */}
                  {/* Ranked last and labelled, never silently dropped:
                      much ski inventory is apartments Google does not
                      classify, and a place we cannot judge is not a
                      place we should hide (owner's rule). */}
                  {/* "Google narrowed the search to the stars you
                      asked for but will not tell us this property's
                      own class" is a different claim from "nobody
                      rated this place", and the two must not share a
                      label. */}
                  {o.star_class_source === "provider_filter" && (
                    <span className="flex-none rounded-full bg-signal-soft px-1.5 py-px text-[10px] font-semibold text-signal"
                          title={t("accommodationVettedTitle")}>
                      {t("accommodationVetted")}
                    </span>
                  )}
                  {o.quality_unverified && o.star_class_source !== "provider_filter" && (
                    <span className="flex-none rounded-full bg-sunken px-1.5 py-px text-[10px] font-semibold text-muted"
                          title={t("accommodationUnratedTitle")}>
                      {t("accommodationUnrated")}
                    </span>
                  )}
                  {o.star_class != null && (
                    <span className="flex-none font-semibold text-ink"
                          title={t("accommodationStarsTitle", { n: String(o.star_class) })}>
                      {"\u2605".repeat(o.star_class)}
                    </span>
                  )}
                  {o.rating != null && (
                    <span className="flex-none" title={o.review_count != null
                      ? t("accommodationReviewsTitle", { n: String(o.review_count) }) : undefined}>
                      {t("accommodationRating", { r: o.rating.toFixed(1) })}
                      {o.review_count != null && (
                        <span className="ms-1 text-subtle">
                          {t("accommodationReviewCount", { n: o.review_count.toLocaleString() })}
                        </span>
                      )}
                    </span>
                  )}
                  <span className="min-w-0 flex-1 truncate">
                    {t("accommodationPerPersonStay", { price: String(Math.round(o.per_person_eur)) })}
                  </span>
                  <span className="flex-none tabular-nums" title={t("tripTotalTooltip")}>
                    {t("flightTripTotal", { total: String(Math.round(
                      tripTotalFor ? tripTotalFor(o.per_person_eur) : o.trip_total_eur)) })}
                  </span>
                </div>
              </SelectableOptionRow>
            ))}
          </OptionRadioGroup>
          {/* Price-only ordering, said out loud rather than implied. */}
          <p className="mt-2 text-[10px] leading-snug text-subtle">{t("accommodationOptionsNote")}</p>
        </>
      )}
    </div>
  );
}
