"use client";

import { useMemo, useState } from "react";
import type { PricePoint } from "./PriceExplorer";
import { formatEUR } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";

/**
 * PRICE BY START DATE AND RESORT -- one row per resort on a shared
 * date axis.
 *
 * WHAT IT REPLACED and why: the previous month grid showed ONE cell
 * per day, holding whichever resort was cheapest that day. That
 * collapses two variables into one channel, and on real data it lied.
 * A measured 13-date window ran 7 Bansko days (EUR912-1,013), 5 Val
 * Thorens days (EUR1,723-1,961) and one Kitzbuehel day, so the view's
 * own headline -- "EUR1,049 less per person than the priciest day in
 * this window" -- was almost entirely Bulgaria-vs-France, not timing.
 * The real timing spread at Bansko is EUR101. Worse, the Val Thorens
 * block was a run of days on which Bansko simply had no result, so the
 * ramp read "these days are expensive" when the truth was "on these
 * days we only found France".
 *
 * THE FIX is to give the two variables two channels:
 *   - along a row  = WHEN, so colour is normalised within that resort;
 *   - across rows  = WHERE, ordered cheapest destination first.
 * Shading therefore always means "cheap for this resort", never "cheap
 * compared with a different country".
 *
 * EVERY CELL IS REAL OR EMPTY -- days the search did not return render
 * blank, never interpolated. The empty run is itself a finding.
 *
 * A row whose prices do not vary (a single date, or identical figures)
 * gets a neutral fill rather than a position on the ramp: with no
 * spread, any shade would be an arbitrary claim.
 */

// Deep (cheap) -> pale (dear). Sequential, single hue: this encodes
// MAGNITUDE, and it must not borrow the piste palette (terrain).
const CHEAP = [12, 74, 110];    // #0c4a6e
const DEAR = [224, 242, 254];   // #e0f2fe

// A column floor, not a fixed width: the grid stretches to fill a
// desktop and scrolls on a phone rather than compressing 24 days into
// 14px slivers with their date labels run together.
const MIN_CELL_PX = 34;

// Beyond this many columns a price cannot sit inside a cell, so the
// figures move to the readout above the grid.
const MAX_COLS_WITH_PRICES = 10;

function ramp(t: number): { bg: string; fg: string } {
  const clamped = Math.max(0, Math.min(1, t));
  const mix = CHEAP.map((c, i) => Math.round(c + (DEAR[i] - c) * clamped));
  return { bg: `rgb(${mix.join(",")})`, fg: clamped < 0.45 ? "#ffffff" : "#0b1526" };
}

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function addDays(d: Date, n: number): Date {
  const out = new Date(d);
  out.setDate(out.getDate() + n);
  return out;
}

interface Row {
  resort: string;
  country: string;
  byDate: Map<string, PricePoint>;
  min: number;
  max: number;
  cheapestDate: string;
  priciestDate: string;
}

export function PriceMatrix({ points, onPick, openable }: {
  points: PricePoint[];
  /**
   * "resort|date" keys that have a result card below. Everything else
   * was priced but did not make the ranked list, so it is shown as a
   * price rather than a control that does nothing.
   */
  openable?: Set<string>;
  /** Jump to that resort's card, opened on that date. */
  onPick?: (resort: string, date: string) => void;
}) {
  const { t, locale } = useTranslation();
  const [hovered, setHovered] = useState<string | null>(null);

  const model = useMemo(() => {
    const dated = points;
    if (dated.length === 0) return null;

    // One entry per (resort, date): the same pair can appear more than
    // once across a multi-resort search, and the cheapest is the one
    // the card would show.
    const perResort = new Map<string, Row>();
    for (const p of dated) {
      const row = perResort.get(p.resort) ?? {
        resort: p.resort,
        country: p.country,
        byDate: new Map<string, PricePoint>(),
        min: Infinity, max: -Infinity, cheapestDate: "", priciestDate: "",
      };
      const seen = row.byDate.get(p.date);
      if (!seen || p.totalEur < seen.totalEur) row.byDate.set(p.date, p);
      perResort.set(p.resort, row);
    }

    for (const row of perResort.values()) {
      for (const [date, p] of row.byDate) {
        if (p.totalEur < row.min) { row.min = p.totalEur; row.cheapestDate = date; }
        if (p.totalEur > row.max) { row.max = p.totalEur; row.priciestDate = date; }
      }
    }

    // Cheapest destination first -- the vertical axis is itself the
    // "where" ranking, so it may as well be sorted like one.
    const rows = [...perResort.values()].sort((a, b) => a.min - b.min);

    const allDates = dated.map((p) => p.date).sort();
    const first = new Date(allDates[0] + "T00:00:00");
    const last = new Date(allDates[allDates.length - 1] + "T00:00:00");
    const span = Math.round((last.getTime() - first.getTime()) / 86_400_000) + 1;
    // Every calendar day in the window, gaps included: a fortnight
    // with no results is a finding, not something to close up.
    const days = Array.from({ length: span }, (_, i) => addDays(first, i));

    return { rows, days, best: rows[0] };
  }, [points]);

  if (!model) return null;
  const { rows, days, best } = model;

  const readout = (() => {
    if (!hovered) return null;
    const [resort, date] = hovered.split("|");
    const hit = rows.find((r) => r.resort === resort)?.byDate.get(date);
    if (!hit) return null;
    return {
      resort,
      date: new Date(date + "T00:00:00")
        .toLocaleDateString(locale, { weekday: "short", day: "numeric", month: "long" }),
      price: formatEUR(hit.totalEur, locale),
    };
  })();

  const showPrices = days.length <= MAX_COLS_WITH_PRICES;

  return (
    <div>
      <div className="flex flex-wrap items-baseline justify-end gap-x-4 gap-y-1">
        <div className="flex items-center gap-2 text-[11px] text-subtle">
          <span>{t("priceMatrixCheap")}</span>
          <span
            aria-hidden="true"
            className="h-2 w-20 rounded-full"
            style={{ background: `linear-gradient(to right, rgb(${CHEAP.join(",")}), rgb(${DEAR.join(",")}))` }}
          />
          <span>{t("priceMatrixDear")}</span>
        </div>
      </div>

      {/* Where a cell's own figure goes when the columns are too
          narrow to hold it. Reserved height so pointing at cells does
          not shift the grid under the pointer. */}
      <p className="mt-2 flex h-5 items-center text-xs text-ink" aria-live="polite">
        {readout ? (
          <>
            <span className="font-semibold">{readout.resort}</span>
            <span className="mx-1.5 text-subtle">·</span>
            <span>{readout.date}</span>
            <span className="mx-1.5 text-subtle">·</span>
            <span className="font-semibold tabular-nums">{readout.price}</span>
          </>
        ) : (
          <span className="text-subtle">{t("priceMatrixReadoutHint")}</span>
        )}
      </p>

      {/* The axis can outrun a phone, so it scrolls -- with the resort
          column pinned, because a row you cannot name is a row you
          cannot read. */}
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-max border-separate border-spacing-0">
          <thead>
            <tr>
              <th className="sticky start-0 z-10 bg-surface" />
              {days.map((day) => {
                const weekday = day.toLocaleDateString(locale, { weekday: "narrow" });
                // Resort weeks conventionally start on a Saturday, and
                // the engine already breaks ties toward one, so the
                // Saturday columns are worth being able to find.
                const saturday = day.getDay() === 6;
                return (
                  <th
                    key={iso(day)}
                    scope="col"
                    style={{ minWidth: MIN_CELL_PX }}
                    className={`pb-1 text-center text-[10px] font-semibold ${
                      saturday ? "text-signal" : "text-subtle"
                    }`}
                  >
                    <span className="block">{weekday}</span>
                    <span className="block font-normal tabular-nums">{day.getDate()}</span>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const flat = row.max === row.min;
              return (
                <tr key={row.resort}>
                  <th
                    scope="row"
                    className="sticky start-0 z-10 bg-surface pe-3 text-start align-middle"
                  >
                    <span className="block whitespace-nowrap text-xs font-semibold text-ink">
                      {row.resort}
                    </span>
                    <span className="block whitespace-nowrap text-[10px] tabular-nums text-subtle">
                      {flat
                        ? formatEUR(row.min, locale)
                        : `${formatEUR(row.min, locale)}–${formatEUR(row.max, locale)}`}
                    </span>
                  </th>
                  {days.map((day) => {
                    const key = iso(day);
                    const hit = row.byDate.get(key);
                    const cellKey = `${row.resort}|${key}`;
                    if (!hit) {
                      return (
                        <td key={cellKey} className="p-0.5">
                          <div className="h-9 rounded-md border border-line/50" />
                        </td>
                      );
                    }
                    // Normalised WITHIN the row: shading answers "when",
                    // never "where".
                    const tPct = flat ? null : (hit.totalEur - row.min) / (row.max - row.min);
                    // Grey, not a pale blue: a single-date row has no
                    // spread to encode, and a pale ramp value would
                    // both claim "expensive" and look like an empty
                    // cell.
                    const tone = tPct === null
                      ? { bg: "rgb(148,163,184)", fg: "#0b1526" }
                      : ramp(tPct);
                    const isRowBest = key === row.cheapestDate && !flat;
                    // See PriceCalendarPerResort: everything outside
                    // the shortlist is our static estimate, which moves
                    // by season band rather than by day.
                    const estimated = !hit.priceIsLive;
                    // Openable only where a card exists below -- see
                    // the prop's note.
                    const canOpen = Boolean(onPick)
                      && (!openable || openable.has(`${row.resort}|${key}`));
                    return (
                      <td key={cellKey} className="p-0.5">
                        <button
                          type="button"
                          disabled={!canOpen}
                          onMouseEnter={() => setHovered(cellKey)}
                          onMouseLeave={() => setHovered(null)}
                          onFocus={() => setHovered(cellKey)}
                          onBlur={() => setHovered(null)}
                          onClick={() => onPick?.(row.resort, key)}
                          title={`${row.resort} — ${day.toLocaleDateString(locale, { day: "numeric", month: "long" })} — ${formatEUR(hit.totalEur, locale)}`}
                          aria-label={t("priceCellOpen", {
                            resort: row.resort,
                            date: day.toLocaleDateString(locale, { day: "numeric", month: "long" }),
                            price: formatEUR(hit.totalEur, locale) })}
                          className={`relative flex h-9 w-full items-center justify-center rounded-md px-0.5 text-[11px] font-bold tabular-nums transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                            hovered === cellKey ? "scale-[1.08]" : ""
                          } ${
                            canOpen ? "cursor-pointer" : "cursor-default"
                          } ${isRowBest ? "ring-2 ring-signal" : ""}`}
                          style={estimated
                            ? { backgroundColor: tone.bg, color: tone.fg,
                                backgroundImage: `repeating-linear-gradient(45deg, ${tone.fg}22 0 3px, transparent 3px 7px)` }
                            : { backgroundColor: tone.bg, color: tone.fg }}
                        >
                          {canOpen && (
                            <span aria-hidden="true"
                                  className="absolute end-0.5 top-0.5 h-1.5 w-1.5 rounded-full"
                                  style={{ backgroundColor: tone.fg, opacity: 1 }} />
                          )}
                          {showPrices
                            ? `${estimated ? "~" : ""}${formatEUR(hit.totalEur, locale)}`
                            : ""}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Two claims, kept apart on purpose: which destination, and --
          separately -- which week within it. */}
      <p className="mt-4 text-sm text-muted">
        {t("priceMatrixWhere", {
          resort: best.resort,
          price: formatEUR(best.min, locale),
          date: new Date(best.cheapestDate + "T00:00:00")
            .toLocaleDateString(locale, { day: "numeric", month: "long" }),
        })}
      </p>
      {best.max > best.min && (
        <p className="mt-1 text-sm text-muted">
          {t("priceMatrixWhen", {
            resort: best.resort,
            date: new Date(best.cheapestDate + "T00:00:00")
              .toLocaleDateString(locale, { day: "numeric", month: "long" }),
            saving: formatEUR(best.max - best.min, locale),
          })}
        </p>
      )}
      <p className="mt-2 text-[11px] leading-snug text-subtle">{t("priceMatrixScaleNote")}</p>
      {points.some((p) => !p.priceIsLive) && (
        <p className="mt-1 text-[11px] leading-snug text-warn">
          {t("priceCalendarEstimatedLegend")}
        </p>
      )}
      <p className="mt-1 text-[11px] leading-snug text-subtle">{t("priceMatrixFlatNote")}</p>
      <p className="mt-1 text-[11px] text-subtle">{t("priceCalendarEmptyNote")}</p>
    </div>
  );
}
