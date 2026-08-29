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
import { ResultCard } from "@/components/ResultCard";
import { SAMPLE_TRIPS, SAMPLE_DATED } from "@/lib/sampleTrips";
import { PriceCalendar } from "@/components/PriceCalendar";

export default function DesignPreview() {
  const trips = [SAMPLE_TRIPS.bansko, SAMPLE_TRIPS.zermatt, SAMPLE_TRIPS.valThorens];
  return (
    <main className="py-10">
      <p className="mx-auto mb-6 max-w-3xl rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-xs text-warn">
        Design harness — real captured payloads, not a live search.
      </p>
      {/* same container the real page uses */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6">
        <PriceCalendar results={SAMPLE_DATED} />
      </section>

      <div className="mx-auto mt-8 max-w-3xl space-y-5 px-4 sm:px-6">
        {trips.map((t) => (
          <ResultCard key={t.resort.name + t.start_date} result={t} maxConnections={1} />
        ))}
      </div>
    </main>
  );
}
