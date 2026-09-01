"use client";

import { useMemo, useState, type CSSProperties } from "react";
import type { PricePoint } from "./PriceExplorer";
import { formatEUR } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";

/**
 * PRICE BY START DATE, ONE RESORT AT A TIME -- a real month grid.
 *
 * This is the original calendar with the confound taken out. The grid
 * used to hold whichever resort was cheapest on each day, so its
 * shading and its "saving" headline mixed WHERE with WHEN (see
 * PriceMatrix's note: a measured window put EUR1,049 of an apparent
 * "timing" saving down to Bulgaria-vs-France). Here the whole grid
 * belongs to ONE resort, chosen above it, so every comparison inside
 * it is a comparison of dates -- which is what a calendar is for.
 *
 * Kept alongside the matrix rather than replacing it: the month layout
 * shows weeks, weekends and the shape of a school holiday far better
 * than a linear axis, and it has room to print every price. What it
 * cannot do is compare destinations, which is the matrix's job.
 *
 * EVERY CELL IS REAL OR EMPTY -- days the search did not return render
 * blank, never interpolated from their neighbours.
 */

const CHEAP = [12, 74, 110];    // #0c4a6e
const DEAR = [224, 242, 254];   // #e0f2fe

function ramp(t: number): { bg: string; fg: string } {
  const clamped = Math.max(0, Math.min(1, t));
  const mix = CHEAP.map((c, i) => Math.round(c + (DEAR[i] - c) * clamped));
  return { bg: `rgb(${mix.join(",")})`, fg: clamped < 0.45 ? "#ffffff" : "#0b1526" };
}

function iso(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function PriceCalendarPerResort({
  points, onPick, openable, onFetchReal, fetching, startWindowKnown = false,
}: {
  points: PricePoint[];
  /**
   * "resort|date" keys that have a result card below. The calendar
   * prices far more days than the ranked list keeps, and a day with no
   * card cannot be opened -- so it is shown as a price, not a button.
   */
  openable?: Set<string>;
  /**
   * Buy a real price for one estimated day. Costs the traveller a
   * credit, so it is always an explicit click, never automatic.
   */
  onFetchReal?: (resort: string, date: string) => void;
  /** "resort|date" currently being fetched, for the cell's own state. */
  fetching?: string | null;
  /**
   * True only when these points are the FULL evaluated grid, where the
   * first and last dated entries really are the first and last valid
   * start dates. From a capped results list they are not, so the
   * "only these days can be a start date" line must stay hidden.
   */
  startWindowKnown?: boolean;
  /** Jump to this resort's card, opened on that date. */
  onPick?: (resort: string, date: string) => void;
}) {
  const { t, locale } = useTranslation();
  const [resort, setResort] = useState<string | null>(null);

  const resorts = useMemo(() => {
    const cheapest = new Map<string, number>();
    for (const p of points) {
      const seen = cheapest.get(p.resort);
      if (seen === undefined || p.totalEur < seen) cheapest.set(p.resort, p.totalEur);
    }
    // Cheapest destination first, matching the matrix's row order so
    // switching views does not reshuffle the same list.
    return [...cheapest.entries()].sort((a, b) => a[1] - b[1]).map(([name]) => name);
  }, [points]);

  const active = resort && resorts.includes(resort) ? resort : resorts[0];

  const model = useMemo(() => {
    if (!active) return null;
    const dated = points.filter((p) => p.resort === active);
    if (dated.length === 0) return null;

    const byDate = new Map<string, PricePoint>();
    for (const p of dated) {
      const seen = byDate.get(p.date);
      if (!seen || p.totalEur < seen.totalEur) byDate.set(p.date, p);
    }
    const entries = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b));
    const prices = entries.map(([, p]) => p.totalEur);
    const min = Math.min(...prices);
    const max = Math.max(...prices);

    // Whole months spanning this resort's first to last dated result,
    // so gaps inside the window stay visible as empty cells.
    const first = new Date(entries[0][0] + "T00:00:00");
    const last = new Date(entries[entries.length - 1][0] + "T00:00:00");
    const months: { label: string; days: (Date | null)[] }[] = [];
    const cursor = new Date(first.getFullYear(), first.getMonth(), 1);
    while (cursor <= last) {
      const y = cursor.getFullYear();
      const m = cursor.getMonth();
      const daysIn = new Date(y, m + 1, 0).getDate();
      const lead = (new Date(y, m, 1).getDay() + 6) % 7;  // Monday-first
      const cells: (Date | null)[] = Array(lead).fill(null);
      for (let d = 1; d <= daysIn; d++) cells.push(new Date(y, m, d));
      months.push({
        label: new Date(y, m, 1).toLocaleDateString(locale, { month: "long", year: "numeric" }),
        days: cells,
      });
      cursor.setMonth(cursor.getMonth() + 1);
    }

    const cheapest = entries.reduce((a, c) => (c[1].totalEur < a[1].totalEur ? c : a));
    // The LAST date a trip can start and still finish inside the
    // search window. Every day after it is blank for a structural
    // reason, not a missing price -- worth saying, because a 1-19 Dec
    // window with 7 nights can only ever start on the 1st-12th, and a
    // calendar that renders the 13th-19th as "no result" reads as
    // broken when it is simply arithmetic.
    const lastStart = entries[entries.length - 1][0];
    const firstStart = entries[0][0];
    return { byDate, min, max, months, cheapest, spread: max - min, firstStart, lastStart };
  }, [points, active, locale]);

  if (!model || !active) return null;
  const { byDate, min, max, months, cheapest, spread, firstStart, lastStart } = model;

  const weekdays = Array.from({ length: 7 }, (_, i) =>
    // 2024-01-01 was a Monday -- a stable anchor for locale-correct
    // short weekday names without hardcoding English.
    new Date(2024, 0, 1 + i).toLocaleDateString(locale, { weekday: "short" })
  );

  return (
    <div>
      {/* A filter, not a tablist: these chips control which resort the
          grid below describes, but there is no tabpanel per chip -- and
          calling them tabs collided with the real tabs in Trip details. */}
      {resorts.length > 1 && (
        <div role="group" aria-label={t("priceCalendarResortPicker")} className="flex flex-wrap gap-1.5">
          {resorts.map((name) => {
            const on = name === active;
            return (
              <button
                key={name}
                type="button"
                aria-pressed={on}
                onClick={() => setResort(name)}
                className={`rounded-full px-3 py-1 text-xs font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                  on ? "bg-signal text-white" : "border border-line text-muted hover:border-signal hover:text-signal"
                }`}
              >
                {name}
              </button>
            );
          })}
        </div>
      )}

      <div className="mt-3 flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <p className="text-xs text-subtle">
          {spread > 0
            ? t("priceCalendarRange", {
                resort: active,
                min: formatEUR(min, locale),
                max: formatEUR(max, locale),
              })
            : t("priceCalendarSinglePrice", { resort: active, price: formatEUR(min, locale) })}
        </p>
        {spread > 0 && (
          <div className="flex items-center gap-2 text-[11px] text-subtle">
            <span className="tabular-nums">{formatEUR(min, locale)}</span>
            <span
              aria-hidden="true"
              className="h-2 w-20 rounded-full"
              style={{ background: `linear-gradient(to right, rgb(${CHEAP.join(",")}), rgb(${DEAR.join(",")}))` }}
            />
            <span className="tabular-nums">{formatEUR(max, locale)}</span>
          </div>
        )}
      </div>

      <div className="mt-3 space-y-6">
        {months.map((month) => (
          <div key={month.label}>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-subtle">
              {month.label}
            </p>
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
                  // Two different blanks. Outside [firstStart,
                  // lastStart] no trip of this length could START
                  // there and still fit the window -- arithmetic, not
                  // a gap in our data.
                  const outOfRange = startWindowKnown && (key < firstStart || key > lastStart);
                  return (
                    <div
                      key={key}
                      title={outOfRange ? t("priceCalendarOutOfRangeTitle") : undefined}
                      // A dashed border means ESTIMATE and nothing
                      // else, so an out-of-window day is simply
                      // fainter rather than dashed too.
                      className={`flex aspect-[5/4] flex-col items-center justify-center rounded-lg border text-[11px] ${
                        outOfRange
                          ? "border-line/25 bg-sunken/30 text-subtle/40"
                          : "border-line/60 text-subtle/60"
                      }`}
                    >
                      {day.getDate()}
                    </div>
                  );
                }
                // Normalised within THIS resort, so the ramp only ever
                // compares dates.
                const tPct = max === min ? 0 : (hit.totalEur - min) / (max - min);
                const { bg, fg } = max === min
                  ? { bg: "rgb(148,163,184)", fg: "#0b1526" }
                  : ramp(tPct);
                const isCheapest = key === cheapest[0] && spread > 0;
                // LIVE QUOTE vs OUR ESTIMATE. Only the shortlisted
                // pairs get live-repriced; the rest carry the static
                // model, which moves by SEASON BAND and not by day --
                // measured, a resort's whole December is two distinct
                // numbers. Shading them like quotes implied a
                // day-by-day precision the figure does not have.
                const estimated = !hit.priceIsLive;
                // A day is openable only if a result CARD exists for
                // it. The calendar prices every evaluated day; the
                // ranked list keeps a dozen. Clicking the other 94%
                // did nothing, which read as broken -- so they render
                // as prices, not buttons.
                const canOpen = Boolean(onPick)
                  && (!openable || openable.has(`${active}|${key}`));
                // FILLED = a real trip we priced and can open.
                // OUTLINED = an estimate only.
                //
                // The previous version marked "openable" with a dot and
                // "estimated" with stripes, which are two different
                // things that mostly coincide -- so a real day could
                // still be striped and it read as noise. One state,
                // one treatment: a filled cell is a trip, an outlined
                // one is a number we worked out.
                // FILL FOLLOWS THE ACTION, not the price's provenance.
                //
                // These were keyed off `estimated` while the click was
                // keyed off `canOpen`, and on real data they diverge:
                // measured against production, 24 days are live-priced
                // and 24 have cards, but only 12 are both -- the
                // repricing set is picked by static score BEFORE
                // repricing, the displayed set by score after. That
                // left twelve days looking solid and openable while
                // doing nothing, which is the dead click all over
                // again. Now: filled means "opens a card", outlined
                // means "click to fetch it". The ~ still marks an
                // estimate, but it no longer decides the shape.
                const cellClass = `relative flex aspect-[5/4] flex-col items-center justify-center rounded-lg px-1 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-signal ${
                  canOpen || onFetchReal ? "cursor-pointer hover:scale-[1.04]" : ""
                } ${isCheapest ? "ring-2 ring-signal ring-offset-1" : ""} ${
                  canOpen ? "" : "border-2 border-dashed"
                }`;
                const cellStyle = canOpen
                  ? { backgroundColor: bg, color: fg }
                  // The ramp colour moves to the BORDER and the text, so
                  // the cell still reads as its price without claiming
                  // to be a trip we can show.
                  : { borderColor: bg, color: "var(--color-muted)",
                      backgroundColor: "transparent" };
                const inner = (
                  <>
                    <span className="text-[10px] opacity-80">{day.getDate()}</span>
                    <span className="text-[11px] font-bold tabular-nums sm:text-xs">
                      {estimated ? "~" : ""}{formatEUR(hit.totalEur, locale)}
                    </span>
                  </>
                );
                if (!canOpen) {
                  // An estimate is worth a real lookup, and that lookup
                  // costs a credit -- so it is an offer, not a silent
                  // dead end.
                  if (onFetchReal) {
                    // The page keys this by "resort|date"; comparing it
                    // against the bare date meant the busy state never
                    // showed and a two-minute fetch looked like a dead
                    // click (measured against production 2026-09-01).
                    const busy = fetching === `${active}|${key}`;
                    return (
                      <button
                        key={key}
                        type="button"
                        disabled={busy}
                        onClick={() => onFetchReal(active, key)}
                        aria-label={t("priceCellFetchReal", {
                          resort: active,
                          date: day.toLocaleDateString(locale, { day: "numeric", month: "long" }),
                        })}
                        title={t("priceCellFetchRealTitle")}
                        className={cellClass}
                        style={cellStyle}
                      >
                        {busy ? (
                          <span className="text-[10px] font-semibold">{t("priceCellFetching")}</span>
                        ) : inner}
                      </button>
                    );
                  }
                  return (
                    <div
                      key={key}
                      title={t("priceCellNotOpenable", { price: formatEUR(hit.totalEur, locale) })}
                      className={cellClass}
                      style={cellStyle}
                    >
                      {inner}
                    </div>
                  );
                }
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onPick?.(active, key)}
                    aria-label={t("priceCellOpen", {
                      resort: active,
                      date: day.toLocaleDateString(locale, { day: "numeric", month: "long" }),
                      price: formatEUR(hit.totalEur, locale),
                    })}
                    className={cellClass}
                    style={cellStyle}
                    title={estimated ? t("priceCellEstimated") : undefined}
                  >
                    {inner}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* A timing claim only -- everything on screen is one resort. */}
      {spread > 0 && (
        <p className="mt-4 text-sm text-muted">
          {/* If either end of the range is an estimate, the "saving" is
              largely the season-band step in our own model, not a
              measured difference between two real quotes. Say which. */}
          {t(byDate.get(cheapest[0])?.priceIsLive
             && [...byDate.values()].every((p) => p.priceIsLive)
               ? "priceCalendarInsightPerResort"
               : "priceCalendarInsightEstimated", {
            resort: active,
            date: new Date(cheapest[0] + "T00:00:00")
              .toLocaleDateString(locale, { day: "numeric", month: "long" }),
            price: formatEUR(cheapest[1].totalEur, locale),
            saving: formatEUR(spread, locale),
          })}
        </p>
      )}
      {onPick && (
        <p className="mt-2 text-[11px] leading-snug text-subtle">
          {t("priceCalendarStateLegend")}
        </p>
      )}
      {[...byDate.values()].some((p) => !p.priceIsLive) && (
        <p className="mt-1 text-[11px] leading-snug text-subtle">
          {t("priceCalendarEstimatedLegend")}
        </p>
      )}
      {startWindowKnown && (
      <p className="mt-1 text-[11px] leading-snug text-subtle">
        {t("priceCalendarStartWindow", {
          first: new Date(firstStart + "T00:00:00").toLocaleDateString(locale, { day: "numeric", month: "long" }),
          last: new Date(lastStart + "T00:00:00").toLocaleDateString(locale, { day: "numeric", month: "long" }),
        })}
      </p>
      )}
      <p className="mt-1 text-[11px] text-subtle">{t("priceCalendarEmptyNote")}</p>
    </div>
  );
}
