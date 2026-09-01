"use client";

/**
 * DESIGN HARNESS -- not part of the product surface.
 *
 * Renders result cards against REAL captured API payloads
 * (lib/sampleTrips.ts) so components can be iterated and screenshotted
 * in seconds instead of waiting ~80s for a live search. Covers the
 * full realistic price range on purpose: Bansko EUR975 (budget),
 * Zermatt EUR1,317, Val Thorens EUR1,740 (premium).
 */
import { useState } from "react";
import { ResultCard } from "@/components/ResultCard";
import { SAMPLE_TRIPS, SAMPLE_DATED } from "@/lib/sampleTrips";
import { PriceExplorer } from "@/components/PriceExplorer";
import { SearchProgress } from "@/components/SearchProgress";

export default function DesignPreview() {
  const trips = [SAMPLE_TRIPS.bansko, SAMPLE_TRIPS.zermatt, SAMPLE_TRIPS.valThorens];
  const [pick, setPick] = useState<{ resort: string; date: string; seq: number } | null>(null);
  const [fetched, setFetched] = useState<string | null>(null);
  // Stand-in for the ranked list: a handful of the priced grid, the
  // way a real search returns ~24 cards against ~192 priced days.
  const CARD_RESULTS = SAMPLE_DATED.filter((_, i) => i % 7 === 0);
  // Grouped exactly as app/page.tsx groups them, so clicking a day in
  // the price views can be exercised here rather than only in a live
  // ~80s search.
  const groups = new Map<string, typeof SAMPLE_DATED>();
  for (const r of CARD_RESULTS) {
    const list = groups.get(r.resort.name);
    if (list) list.push(r);
    else groups.set(r.resort.name, [r]);
  }
  return (
    <main className="py-10">
      <p className="mx-auto mb-6 max-w-3xl rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
        Design harness — real captured payloads, not a live search.
      </p>
      {/* The search progress bar, which the real page only shows to a
          signed-in user mid-search. */}
      <section className="mx-auto max-w-5xl px-4 pb-8 sm:px-6">
        <SearchProgress />
      </section>

      {/* same container the real page uses */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6">
        {/* Mirrors production: the calendar is fed the FULL priced
            grid, while cards exist only for the ranked few -- so the
            "openable vs priced-only" split is actually exercised here
            rather than only in a live search. */}
        <PriceExplorer
          results={CARD_RESULTS}
          datePrices={SAMPLE_DATED.filter((r) => r.start_date).map((r) => ({
            resort_name: r.resort.name,
            country: r.resort.country,
            start_date: r.start_date!,
            total_eur: r.cost.total_eur,
            within_budget: r.within_budget,
            // Mirrors production: only the shortlisted pairs are live;
            // everything else carries the static estimate.
            price_is_live: CARD_RESULTS.includes(r)
              && Boolean(r.cost.flight_price_is_live && r.cost.accommodation_price_is_live),
          }))}
          onPick={(resort, date) => setPick((p) => ({ resort, date, seq: (p?.seq ?? 0) + 1 }))}
          onFetchReal={(resort, date) => setFetched(`${resort}|${date}`)}
          fetching={null}
        />
        {fetched && (
          <p className="mt-2 text-xs text-signal">
            harness: would spend 1 credit on {fetched}
          </p>
        )}
      </section>

      <div className="mx-auto mt-8 max-w-3xl space-y-5 px-4 sm:px-6">
        {[...groups.entries()].map(([name, list]) => (
          <ResultCard key={name} result={list[0]} variants={list} maxConnections={1}
                      focus={pick && pick.resort === name ? { date: pick.date, seq: pick.seq } : null} />
        ))}
      </div>

      {/* The standalone captures stay below, for component-level work. */}
      <div className="mx-auto mt-10 max-w-3xl space-y-5 px-4 sm:px-6">
        {trips.map((t) => (
          <ResultCard key={t.resort.name + t.start_date} result={t} maxConnections={1} />
        ))}
      </div>
    </main>
  );
}
