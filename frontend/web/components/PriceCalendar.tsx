"use client";

import { useMemo, useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";

/**
 * PRICE BY START DATE -- a real month grid, tinted by trip price.
 *
 * WHAT IT REPLACED and why: this used to be a `flex-wrap` row of 80px
 * chips. With a real 13-date result set that renders as two ragged
 * rows in which "30 Jan" sits immediately beside "19 Jan" -- the
 * ten-day gap between them is invisible, and so is every week
 * boundary. The product's central claim is "travelling the week of
 * 20 Jan saves EUR173", and you cannot see a WEEK in a wrapped list.
 * So: an actual calendar, weekday-aligned, gaps included.
 *
 * EVERY CELL IS REAL OR EMPTY. Days the search did not return (pruned,
 * out of window, or no resort fit the budget) render as blank cells,
 * never interpolated from their neighbours. A heat-map that guesses
 * the middle of a gap is inventing prices.
 *
 * COLOUR: one sequential ramp, deep = cheap, stated in the legend so
 * the direction is never guessed. Full lightness range rather than the
 * old alpha wash, which made EUR912 and EUR966 indistinguishable.
 * Colour is never the sole carrier -- every priced cell prints its own
 * figure, and the headline saving is written out in words.
 */

// Deep (cheap) -> pale (expensive). Sequential, single hue: this
// encodes MAGNITUDE, so it must not be a multi-hue scale, and it must
// not borrow the piste palette (reserved for terrain difficulty).
const CHEAP = [12, 74, 110];    // #0c4a6e
const DEAR = [224, 242, 254];   // #e0f2fe

function ramp(t: number): { bg: string; fg: string } {
  const clamped = Math.max(0, Math.min(1, t));
  const mix = CHEAP.map((c, i) => Math.round(c + (DEAR[i] - c) * clamped));
  // Flip the label colour where the fill goes dark, so the price stays
  // legible at both ends of the scale.
  return { bg: `rgb(${mix.join(",")})`, fg: clamped < 0.45 ? "#ffffff" : "#0b1526" };
}

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function PriceCalendar({ results }: { results: TripResult[] }) {
  const { t, locale } = useTranslation();
  const [hovered, setHovered] = useState<string | null>(null);

  const model = useMemo(() => {
    const dated = results.filter((r) => r.start_date);
    if (dated.length === 0) return null;

    // Cheapest option per start date -- a date appears once per resort
    // searched, and the calendar answers "what is the best deal that
    // day", not "what did every resort cost".
    const byDate = new Map<string, TripResult>();
    for (const r of dated) {
      const seen = byDate.get(r.start_date!);
      if (!seen || r.cost.total_eur < seen.cost.total_eur) byDate.set(r.start_date!, r);
    }
    const entries = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b));
    const prices = entries.map(([, r]) => r.cost.total_eur);
    const min = Math.min(...prices);
    const max = Math.max(...prices);

    // Whole months spanning the first to last dated result, so gaps
    // inside the window are visible as empty cells.
    const first = new Date(entries[0][0] + "T00:00:00");
    const last = new Date(entries[entries.length - 1][0] + "T00:00:00");
    const months: { label: string; days: (Date | null)[] }[] = [];
    const cursor = new Date(first.getFullYear(), first.getMonth(), 1);
    while (cursor <= last) {
      const y = cursor.getFullYear();
      const m = cursor.getMonth();
      const daysIn = new Date(y, m + 1, 0).getDate();
      // Monday-first, matching European convention.
      const lead = (new Date(y, m, 1).getDay() + 6) % 7;
      const cells: (Date | null)[] = Array(lead).fill(null);
      for (let d = 1; d <= daysIn; d++) cells.push(new Date(y, m, d));
      months.push({
        label: new Date(y, m, 1).toLocaleDateString(locale, { month: "long", year: "numeric" }),
        days: cells,
      });
      cursor.setMonth(cursor.getMonth() + 1);
    }

    const cheapest = entries.reduce((a, c) => (c[1].cost.total_eur < a[1].cost.total_eur ? c : a));
    const priciest = entries.reduce((a, c) => (c[1].cost.total_eur > a[1].cost.total_eur ? c : a));
    return { byDate, min, max, months, cheapest, priciest,
             spread: priciest[1].cost.total_eur - cheapest[1].cost.total_eur };
  }, [results, locale]);

  if (!model) return null;
  const { byDate, min, max, months, cheapest, spread } = model;

  const weekdays = Array.from({ length: 7 }, (_, i) =>
    // 2024-01-01 was a Monday -- a stable anchor for locale-correct
    // short weekday names without hardcoding English.
    new Date(2024, 0, 1 + i).toLocaleDateString(locale, { weekday: "short" })
  );

  return (
    <section className="mt-8 rounded-2xl border border-line bg-surface p-4 sm:p-6">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h4 className="text-sm font-semibold text-ink">{t("priceByStartDate")}</h4>
        {/* Legend: says which end is cheap, so the ramp is never guessed. */}
        <div className="flex items-center gap-2 text-[11px] text-subtle">
          <span className="tabular-nums">{formatEUR(min, locale)}</span>
          <span
            aria-hidden="true"
            className="h-2 w-24 rounded-full"
            style={{ background: `linear-gradient(to right, rgb(${CHEAP.join(",")}), rgb(${DEAR.join(",")}))` }}
          />
          <span className="tabular-nums">{formatEUR(max, locale)}</span>
        </div>
      </div>

      <div className="mt-4 space-y-6">
        {months.map((month) => (
          <div key={month.label}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-subtle">
              {month.label}
            </p>
            {/* Capped rather than full-bleed: at 1440px a 1/7 square
                cell is ~190px and one month runs 1400px tall, which
                turns the flagship view into a scroll. ~100px cells
                keep every price legible without dominating. */}
            <div className="grid grid-cols-7 gap-1 sm:gap-2">
              {weekdays.map((w) => (
                <div key={w} className="pb-1 text-center text-[10px] font-semibold uppercase text-subtle">
                  {w}
                </div>
              ))}
              {month.days.map((day, i) => {
                if (!day) return <div key={`blank-${i}`} />;
                const key = iso(day);
                const hit = byDate.get(key);
                if (!hit) {
                  // No result for this day. Shown, but plainly empty --
                  // never shaded, which would imply a price.
                  return (
                    <div
                      key={key}
                      className="flex aspect-[5/4] flex-col items-center justify-center rounded-lg border border-line/60 text-[11px] text-subtle/60"
                    >
                      {day.getDate()}
                    </div>
                  );
                }
                const tPct = max === min ? 0 : (hit.cost.total_eur - min) / (max - min);
                const { bg, fg } = ramp(tPct);
                const isCheapest = key === cheapest[0];
                return (
                  <button
                    key={key}
                    type="button"
                    onMouseEnter={() => setHovered(key)}
                    onMouseLeave={() => setHovered(null)}
                    onFocus={() => setHovered(key)}
                    onBlur={() => setHovered(null)}
                    title={`${hit.resort.name} — ${formatEUR(hit.cost.total_eur, locale)}`}
                    className={`flex aspect-[5/4] flex-col items-center justify-center rounded-lg px-1 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                      hovered === key ? "scale-[1.06]" : ""
                    } ${isCheapest ? "ring-2 ring-signal ring-offset-1" : ""}`}
                    style={{ backgroundColor: bg, color: fg }}
                  >
                    <span className="text-[10px] opacity-80">{day.getDate()}</span>
                    <span className="text-[11px] font-bold tabular-nums sm:text-xs">
                      {formatEUR(hit.cost.total_eur, locale)}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* The insight, in words -- the point of the whole view. */}
      <p className="mt-4 text-sm text-muted">
        {t("priceCalendarInsight", {
          date: new Date(cheapest[0] + "T00:00:00").toLocaleDateString(locale, { day: "numeric", month: "long" }),
          price: formatEUR(cheapest[1].cost.total_eur, locale),
          resort: cheapest[1].resort.name,
          saving: formatEUR(spread, locale),
        })}
      </p>
      <p className="mt-1 text-[11px] text-subtle">{t("priceCalendarEmptyNote")}</p>
    </section>
  );
}
