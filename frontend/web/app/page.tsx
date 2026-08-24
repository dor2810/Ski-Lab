"use client";

import { useEffect, useState } from "react";
import { Hero } from "@/components/Hero";
import { ProblemSection } from "@/components/ProblemSection";
import { HowItWorks } from "@/components/HowItWorks";
import { SearchCard, type SearchMode, type SearchOutcome } from "@/components/SearchCard";
import { ResultCard } from "@/components/ResultCard";
import { PriceCalendar } from "@/components/PriceCalendar";
import { WhySkiLab } from "@/components/WhySkiLab";
import { Footer } from "@/components/Footer";
import { searchFixedDates, ApiError } from "@/lib/api";
import { DEFAULT_RAW_WEIGHTS, normalizeWeights } from "@/components/PrioritySliders";

export default function Home() {
  const [mode, setMode] = useState<SearchMode>("fixed");
  const [outcome, setOutcome] = useState<SearchOutcome | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [initialError, setInitialError] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);

  // Populate the results section with a REAL search on first load, using
  // sensible defaults -- not hardcoded mock numbers. The brand deck asked
  // for "genuine figures from the project's database, not invented";
  // running an actual search against the live backend is strictly more
  // honest than hand-typing a partial example (only one of the four
  // reference resorts came with a full cost breakdown to begin with).
  //
  // DELIBERATELY NO outbound_date HERE: passing one triggers live
  // flight+accommodation repricing for up to 10 resorts (rank_trips'
  // live_reprice_n default) via SerpApi -- fine for a user-initiated
  // search (they're already waiting on a spinner they asked for), but
  // wrong for an unconditional call on every single page load: it's
  // slow (~20s, measured) AND spends real, metered SerpApi quota on
  // every visitor before they've asked for anything. Omitting the date
  // gives a fast, free, static-estimate preview instead; the actual
  // search form below always supplies a real date and gets live pricing.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await searchFixedDates({
          budget_eur_per_person: 1500,
          group_size: 2,
          skill_level: "intermediate",
          accommodation_tier: "standard",
          food_profile: "normal",
          equipment_tier: "standard",
          trip_nights: 5,
          top_n: 4,
          weights: normalizeWeights(DEFAULT_RAW_WEIGHTS),
        });
        if (!cancelled) {
          setOutcome({ mode: "fixed", results: data.results, livePricingActive: data.live_pricing_active });
        }
      } catch (err) {
        if (!cancelled) {
          setInitialError(
            err instanceof ApiError
              ? `The search engine is warming up or unavailable (${err.message}). Try a search below.`
              : "Couldn't reach the search engine yet. The free-tier backend may still be starting up -- try a search below in a moment."
          );
        }
      } finally {
        if (!cancelled) setInitialLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function scrollToSearch(nextMode: SearchMode) {
    setMode(nextMode);
    document.getElementById("search")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <>
      <Hero onPlanTrip={() => scrollToSearch("fixed")} onFindDeal={() => scrollToSearch("flexible")} />
      <ProblemSection />
      <HowItWorks />

      <SearchCard
        mode={mode}
        onModeChange={setMode}
        onSearchStart={() => setSearching(true)}
        onOutcome={(o) => {
          setOutcome(o);
          setSearching(false);
        }}
      />

      <section className="mx-auto max-w-3xl px-6 pb-20">
        {(initialLoading || searching) && (
          <p className="animate-rise-in text-center text-sm text-ice/50">
            {initialLoading ? "Finding real trips…" : "Searching…"}
          </p>
        )}

        {!initialLoading && initialError && !outcome && (
          <p className="text-center text-sm text-amber-300/80">{initialError}</p>
        )}

        {outcome && (
          <>
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                {outcome.mode === "flexible" ? "Best deals in your window" : "Top trips for your dates"}
              </h2>
              <span className="text-xs text-ice/40">
                {outcome.livePricingActive ? "Live pricing active" : "Estimated pricing"}
              </span>
            </div>

            {outcome.results.length === 0 ? (
              <p className="text-sm text-ice/60">No trips found for those settings — try a wider budget or date range.</p>
            ) : (
              <div className="space-y-5">
                {outcome.results.map((r, i) => (
                  <ResultCard key={`${r.resort.name}-${r.start_date ?? i}`} result={r} />
                ))}
              </div>
            )}

            {outcome.mode === "flexible" && <PriceCalendar results={outcome.results} />}
          </>
        )}
      </section>

      <WhySkiLab />
      <Footer />
    </>
  );
}
