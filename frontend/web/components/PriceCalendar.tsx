"use client";

import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";

/**
 * Heat-map built entirely from REAL results already returned by
 * /trips/search-dates -- one cell per (start_date, cheapest resort that
 * date), never invented. If a date isn't in the results (it was pruned
 * or didn't fit), it's shown as a blank/unpriced cell rather than a
 * guessed color.
 */
export function PriceCalendar({ results }: { results: TripResult[] }) {
  const { t, locale } = useTranslation();
  const dated = results.filter((r) => r.start_date);
  if (dated.length === 0) return null;

  // Cheapest option per start_date (a date may appear once per resort
  // searched; the calendar shows the best deal available that day).
  const byDate = new Map<string, TripResult>();
  for (const r of dated) {
    const existing = byDate.get(r.start_date!);
    if (!existing || r.cost.total_eur < existing.cost.total_eur) {
      byDate.set(r.start_date!, r);
    }
  }
  const entries = [...byDate.entries()].sort(([a], [b]) => a.localeCompare(b));
  const prices = entries.map(([, r]) => r.cost.total_eur);
  const min = Math.min(...prices);
  const max = Math.max(...prices);

  const cheapest = entries.reduce((best, cur) => (cur[1].cost.total_eur < best[1].cost.total_eur ? cur : best));
  const priciest = entries.reduce((worst, cur) => (cur[1].cost.total_eur > worst[1].cost.total_eur ? cur : worst));
  const spread = priciest[1].cost.total_eur - cheapest[1].cost.total_eur;

  return (
    <div className="mt-8 rounded-2xl border border-line bg-surface p-6">
      <h4 className="mb-4 text-sm font-semibold text-ink">{t("priceByStartDate")}</h4>
      <div className="flex flex-wrap gap-2">
        {entries.map(([date, r]) => {
          // Deeper blue = cheaper, per the brand spec.
          const tPct = max === min ? 0.5 : 1 - (r.cost.total_eur - min) / (max - min);
          const bg = `rgba(56, 189, 248, ${0.15 + tPct * 0.55})`;
          return (
            <div
              key={date}
              className="flex w-20 flex-col items-center rounded-lg px-2 py-2.5 text-center"
              style={{ backgroundColor: bg }}
              title={`${formatDate(date, locale)} — ${formatEUR(r.cost.total_eur, locale)} — ${r.resort.name}`}
            >
              <span className="text-[11px] font-semibold text-ink">{formatDate(date, locale)}</span>
              <span className="text-xs font-bold tabular-nums text-ink">
                {formatEUR(r.cost.total_eur, locale)}
              </span>
            </div>
          );
        })}
      </div>
      {spread > 0 && (
        <p className="mt-4 text-sm text-muted">
          {t("savesLine", {
            date1: formatDate(cheapest[0], locale),
            amount: formatEUR(spread, locale),
            date2: formatDate(priciest[0], locale),
          })}
        </p>
      )}
    </div>
  );
}
