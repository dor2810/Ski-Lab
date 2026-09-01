"use client";

import { useState } from "react";
import type { TripResult, DatePrice } from "@/lib/api";
import { useTranslation } from "@/lib/i18n/context";
import { PriceMatrix } from "./PriceMatrix";
import { PriceCalendarPerResort } from "./PriceCalendarPerResort";

/**
 * The two ways of reading the same prices, behind one switch.
 *
 * They answer different questions and neither subsumes the other:
 *
 *   COMPARE  (matrix) -- every resort on one date axis. The only view
 *            that can rank destinations, and the only one that shows
 *            a date range no resort covers.
 *   CALENDAR (month grid, one resort) -- weeks, weekends and holiday
 *            shape, with room to print every price. It cannot compare
 *            destinations, which is exactly why it is per-resort:
 *            mixing them is what made the original calendar misread
 *            a EUR1,049 destination gap as a timing saving.
 *
 * Defaults to COMPARE because the flexible-dates search is answering
 * "which resort AND which week", and the matrix is the view that holds
 * both halves of that answer at once.
 */

type View = "compare" | "calendar";

/**
 * One priced day, whatever produced it. The date-range search returns
 * a full grid (`date_prices`); a fixed-date search only has its
 * results. Both collapse to this so the two views never care which.
 */
export interface PricePoint {
  resort: string;
  country: string;
  date: string;
  totalEur: number;
  withinBudget: boolean;
  priceIsLive: boolean;
}

export function pointsFrom(results: TripResult[], datePrices?: DatePrice[]): PricePoint[] {
  // Prefer the full grid: `results` is capped for the cards, and
  // drawing a calendar from it leaves priced days blank.
  if (datePrices && datePrices.length > 0) {
    return datePrices.map((d) => ({
      resort: d.resort_name,
      country: d.country,
      date: d.start_date,
      totalEur: d.total_eur,
      withinBudget: d.within_budget,
      priceIsLive: d.price_is_live,
    }));
  }
  return results
    .filter((r) => r.start_date)
    .map((r) => ({
      resort: r.resort.name,
      country: r.resort.country,
      date: r.start_date!,
      totalEur: r.cost.total_eur,
      withinBudget: r.within_budget,
      priceIsLive: Boolean(r.cost.flight_price_is_live && r.cost.accommodation_price_is_live),
    }));
}

export function PriceExplorer({ results, datePrices, onPick, onFetchReal, fetching }: {
  results: TripResult[];
  datePrices?: DatePrice[];
  /** Spend a credit to price one estimated day for real. */
  onFetchReal?: (resort: string, date: string) => void;
  fetching?: string | null;
  /** Open the card for a resort on a given start date. */
  onPick?: (resort: string, date: string) => void;
}) {
  const { t } = useTranslation();
  // The month calendar leads: it is the view people recognise, and it
  // answers "when should I go" for one resort at a time, which is the
  // question a date-range search was asking.
  const [view, setView] = useState<View>("calendar");

  const points = pointsFrom(results, datePrices);
  if (points.length === 0) return null;
  // Only the full evaluated grid lets us say "these are the only dates
  // a trip could start" -- there, the series IS the candidate list.
  // Derived from a capped results list it would be a guess dressed as
  // arithmetic, so the calendar keeps quiet about it.
  const startWindowKnown = Boolean(datePrices && datePrices.length > 0);

  // WHICH DAYS CAN ACTUALLY BE OPENED. The calendar draws every day the
  // search priced; the cards below exist only for the ranked few. On a
  // December search that is 192 priced days against 12 cards, so 94% of
  // the grid had nothing to open -- clicking them looked broken.
  // Raising the card count barely helps (24 cards still leaves 88%), so
  // the cells say which is which instead: a day with a card is a
  // button, a day without is a price.
  const openable = new Set(
    results.filter((r) => r.start_date).map((r) => `${r.resort.name}|${r.start_date}`)
  );

  const tabs: { key: View; label: string }[] = [
    { key: "compare", label: t("priceViewCompare") },
    { key: "calendar", label: t("priceViewCalendar") },
  ];

  return (
    <section className="mt-8 rounded-2xl border border-line bg-surface p-4 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h4 className="text-sm font-semibold text-ink">
          {view === "compare" ? t("priceMatrixTitle") : t("priceByStartDateTitle")}
        </h4>
        <div className="flex rounded-full border border-line p-0.5" role="group" aria-label={t("priceViewSwitch")}>
          {tabs.map((tab) => {
            const on = view === tab.key;
            return (
              <button
                key={tab.key}
                type="button"
                onClick={() => setView(tab.key)}
                aria-pressed={on}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                  on ? "bg-signal text-white" : "text-muted hover:text-signal"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4">
        {view === "compare"
          ? <PriceMatrix points={points} onPick={onPick} openable={openable} />
          : <PriceCalendarPerResort points={points} onPick={onPick} openable={openable}
                                    onFetchReal={onFetchReal} fetching={fetching}
                                    startWindowKnown={startWindowKnown} />}
      </div>
    </section>
  );
}
