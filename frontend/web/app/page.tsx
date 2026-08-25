"use client";

import { useEffect, useState } from "react";
import { Hero } from "@/components/Hero";
import { ProblemSection } from "@/components/ProblemSection";
import { HowItWorks } from "@/components/HowItWorks";
import { SearchCard, type SearchOutcome } from "@/components/SearchCard";
import { ResultCard } from "@/components/ResultCard";
import { PriceCalendar } from "@/components/PriceCalendar";
import { WhySkiLab } from "@/components/WhySkiLab";
import { Footer } from "@/components/Footer";
import { searchFixedDates, ApiError, type TripResult } from "@/lib/api";
import { DEFAULT_RAW_WEIGHTS, normalizeWeights } from "@/components/PrioritySliders";

export default function Home() {
  // Real search results from the form below (SearchCard always calls
  // /trips/search-dates -- see its own comment on why there's no
  // separate "fixed date" mode any more: a date range no wider than the
  // trip length already degrades to exactly one candidate date).
  const [outcome, setOutcome] = useState<SearchOutcome | null>(null);
  const [searching, setSearching] = useState(false);

  // Fast, quota-free PREVIEW shown before the user has searched anything
  // -- separate state from `outcome` because it comes from a different,
  // non-dated call (searchFixedDates, no outbound_date -- see below) and
  // is replaced outright the first time a real search runs.
  const [preview, setPreview] = useState<TripResult[] | null>(null);
  const [previewLoading, setPreviewLoading] = useState(true);
  const [previewError, setPreviewError] = useState<string | null>(null);

  // Populate the results section with a REAL search on first load, using
  // sensible defaults -- not hardcoded mock numbers. The brand deck asked
  // for "genuine figures from the project's database, not invented";
  // running an actual search against the live backend is strictly more
  // honest than hand-typing a partial example.
  //
  // DELIBERATELY NO outbound_date HERE: passing one triggers live
  // flight+accommodation repricing for up to 10 resorts (rank_trips'
  // live_reprice_n default) via SerpApi -- fine for a user-initiated
  // search (they're already waiting on a spinner they asked for), but
  // wrong for an unconditional call on every single page load: it's
  // slow (~20s, measured) AND spends real, metered SerpApi quota on
  // every visitor before they've asked for anything. Omitting the date
  // gives a fast, free, static-estimate preview instead.
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
        if (!cancelled) setPreview(data.results);
      } catch (err) {
        if (!cancelled) {
          setPreviewError(
            err instanceof ApiError
              ? `The search engine is warming up or unavailable (${err.message}). Try a search below.`
              : "Couldn't reach the search engine yet. The free-tier backend may still be starting up -- try a search below in a moment."
          );
        }
      } finally {
        if (!cancelled) setPreviewLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function scrollToSearch() {
    document.getElementById("search")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const showingRealSearch = outcome !== null;
  const displayedResults = showingRealSearch ? outcome!.results : preview;

  return (
    <>
      <Hero onPlanTrip={scrollToSearch} />
      <ProblemSection />
      <HowItWorks />

      <SearchCard
        onSearchStart={() => setSearching(true)}
        onOutcome={(o) => {
          setOutcome(o);
          setSearching(false);
        }}
      />

      <section className="mx-auto max-w-3xl px-6 pb-20">
        {(previewLoading || searching) && (
          <p className="animate-rise-in text-center text-sm text-ice/50">
            {searching ? "Searching…" : "Finding real trips…"}
          </p>
        )}

        {!previewLoading && previewError && !showingRealSearch && (
          <p className="text-center text-sm text-amber-300/80">{previewError}</p>
        )}

        {displayedResults && !searching && (
          <>
            <div className="mb-6 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-white">
                {showingRealSearch ? "Best trips for your search" : "Example trips right now"}
              </h2>
              {showingRealSearch && (
                <span className="text-xs text-ice/40">
                  {outcome!.livePricingActive ? "Live pricing active" : "Estimated pricing"}
                </span>
              )}
            </div>

            {displayedResults.length === 0 ? (
              <p className="text-sm text-ice/60">No trips found for those settings — try a wider budget or date range.</p>
            ) : (
              <div className="space-y-5">
                {displayedResults.map((r, i) => (
                  <ResultCard key={`${r.resort.name}-${r.start_date ?? i}`} result={r} />
                ))}
              </div>
            )}

            {showingRealSearch && <PriceCalendar results={outcome!.results} />}
          </>
        )}
      </section>

      <WhySkiLab />
      <Footer />
    </>
  );
}
