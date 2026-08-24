"use client";

import { useState } from "react";
import {
  searchFixedDates,
  searchFlexibleWindow,
  ApiError,
  type SkillLevel,
  type AccommodationTier,
  type FoodProfile,
  type TransferMode,
  type TripResult,
} from "@/lib/api";
import { todayPlusDays } from "@/lib/format";
import {
  PrioritySliders,
  DEFAULT_RAW_WEIGHTS,
  normalizeWeights,
  type RawWeights,
} from "./PrioritySliders";

export type SearchMode = "fixed" | "flexible";

export interface SearchOutcome {
  mode: SearchMode;
  results: TripResult[];
  livePricingActive: boolean;
  candidateDates?: number;
}

const SKILL_LEVELS: SkillLevel[] = ["beginner", "intermediate", "advanced", "expert"];
const ACCOM_TIERS: AccommodationTier[] = ["budget", "standard", "luxury"];
const FOOD_PROFILES: FoodProfile[] = ["budget", "normal", "luxury"];
const TRANSFER_MODES: { value: TransferMode; label: string }[] = [
  { value: "shared_shuttle", label: "Shared shuttle" },
  { value: "private_transfer", label: "Private transfer" },
  { value: "train", label: "Train" },
  { value: "bus", label: "Bus" },
];

function fieldClass() {
  return "w-full rounded-lg border border-white/15 bg-navy px-3 py-2.5 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky";
}
function labelClass() {
  return "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-ice/60";
}

export function SearchCard({
  mode,
  onModeChange,
  onOutcome,
  onSearchStart,
}: {
  mode: SearchMode;
  onModeChange: (m: SearchMode) => void;
  onOutcome: (outcome: SearchOutcome) => void;
  onSearchStart: () => void;
}) {
  // Fixed-date fields
  const [checkIn, setCheckIn] = useState(todayPlusDays(30));
  const [checkOut, setCheckOut] = useState(todayPlusDays(36));
  // Flexible-window fields
  const [earliest, setEarliest] = useState(todayPlusDays(30));
  const [latest, setLatest] = useState(todayPlusDays(40));
  const [tripNights, setTripNights] = useState(6);

  const [travellers, setTravellers] = useState(2);
  const [skillLevel, setSkillLevel] = useState<SkillLevel>("intermediate");
  const [budget, setBudget] = useState(1500);
  const [weights, setWeights] = useState<RawWeights>(DEFAULT_RAW_WEIGHTS);

  const [prefsOpen, setPrefsOpen] = useState(false);
  const [accomTier, setAccomTier] = useState<AccommodationTier>("standard");
  const [foodProfile, setFoodProfile] = useState<FoodProfile>("normal");
  const [transferModes, setTransferModes] = useState<Set<TransferMode>>(new Set());
  const [maxConnections, setMaxConnections] = useState<string>(""); // "" = no preference

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleTransferMode(m: TransferMode) {
    setTransferModes((prev) => {
      const next = new Set(prev);
      next.has(m) ? next.delete(m) : next.add(m);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const common = {
      budget_eur_per_person: budget,
      group_size: travellers,
      skill_level: skillLevel,
      accommodation_tier: accomTier,
      food_profile: foodProfile,
      equipment_tier: "standard" as const,
      max_connections: maxConnections === "" ? null : Number(maxConnections),
      preferred_transfer_modes: transferModes.size > 0 ? [...transferModes] : null,
      weights: normalizeWeights(weights),
    };

    setLoading(true);
    onSearchStart();
    try {
      if (mode === "fixed") {
        const nights = Math.round(
          (new Date(checkOut).getTime() - new Date(checkIn).getTime()) / 86_400_000
        );
        if (!(nights > 0)) {
          setError("Check-out must be after check-in.");
          return;
        }
        const data = await searchFixedDates({
          ...common,
          trip_nights: nights,
          outbound_date: checkIn,
          top_n: 6,
        });
        onOutcome({ mode, results: data.results, livePricingActive: data.live_pricing_active });
      } else {
        const data = await searchFlexibleWindow({
          ...common,
          trip_nights: tripNights,
          earliest_date: earliest,
          latest_date: latest,
          top_n: 12,
        });
        onOutcome({
          mode,
          results: data.results,
          livePricingActive: data.live_pricing_active,
          candidateDates: data.candidate_dates_per_resort,
        });
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="search" className="mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-white/10 bg-midnight p-6 sm:p-8">
        <div className="mb-7 grid grid-cols-2 gap-2 rounded-xl bg-navy p-1">
          <button
            type="button"
            onClick={() => onModeChange("fixed")}
            className={`rounded-lg py-2.5 text-sm font-semibold transition-colors ${
              mode === "fixed" ? "bg-signal text-white" : "text-ice/60 hover:text-white"
            }`}
          >
            Plan my trip
          </button>
          <button
            type="button"
            onClick={() => onModeChange("flexible")}
            className={`rounded-lg py-2.5 text-sm font-semibold transition-colors ${
              mode === "flexible" ? "bg-signal text-white" : "text-ice/60 hover:text-white"
            }`}
          >
            Find me a deal
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className={labelClass()}>Departure city</label>
            <input value="Tel Aviv (TLV)" disabled className={`${fieldClass()} opacity-60`} />
          </div>

          {mode === "fixed" ? (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label htmlFor="checkin" className={labelClass()}>Check-in</label>
                <input
                  id="checkin"
                  type="date"
                  value={checkIn}
                  onChange={(e) => setCheckIn(e.target.value)}
                  className={fieldClass()}
                  required
                />
              </div>
              <div>
                <label htmlFor="checkout" className={labelClass()}>Check-out</label>
                <input
                  id="checkout"
                  type="date"
                  value={checkOut}
                  onChange={(e) => setCheckOut(e.target.value)}
                  className={fieldClass()}
                  required
                />
              </div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label htmlFor="earliest" className={labelClass()}>Earliest date</label>
                  <input
                    id="earliest"
                    type="date"
                    value={earliest}
                    onChange={(e) => setEarliest(e.target.value)}
                    className={fieldClass()}
                    required
                  />
                </div>
                <div>
                  <label htmlFor="latest" className={labelClass()}>Latest return</label>
                  <input
                    id="latest"
                    type="date"
                    value={latest}
                    onChange={(e) => setLatest(e.target.value)}
                    className={fieldClass()}
                    required
                  />
                </div>
              </div>
              <div>
                <label htmlFor="nights" className={labelClass()}>Trip length (nights)</label>
                <input
                  id="nights"
                  type="number"
                  min={1}
                  max={30}
                  value={tripNights}
                  onChange={(e) => setTripNights(Number(e.target.value))}
                  className={fieldClass()}
                  required
                />
              </div>
            </>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="travellers" className={labelClass()}>Travellers</label>
              <input
                id="travellers"
                type="number"
                min={1}
                max={20}
                value={travellers}
                onChange={(e) => setTravellers(Number(e.target.value))}
                className={fieldClass()}
                required
              />
            </div>
            <div>
              <label htmlFor="skill" className={labelClass()}>Skill level</label>
              <select
                id="skill"
                value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                className={fieldClass()}
              >
                {SKILL_LEVELS.map((s) => (
                  <option key={s} value={s} className="bg-navy">
                    {s[0].toUpperCase() + s.slice(1)}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="budget" className={labelClass()}>Budget per person (EUR)</label>
            <input
              id="budget"
              type="number"
              min={1}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className={fieldClass()}
              required
            />
          </div>

          <div>
            <p className={labelClass()}>Priorities</p>
            <PrioritySliders value={weights} onChange={setWeights} />
          </div>

          <div className="border-t border-white/10 pt-4">
            <button
              type="button"
              onClick={() => setPrefsOpen((o) => !o)}
              className="text-sm font-semibold text-sky hover:text-sky/80"
            >
              {prefsOpen ? "Hide optional preferences" : "Optional preferences"}
            </button>

            {prefsOpen && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label htmlFor="accom" className={labelClass()}>Accommodation tier</label>
                    <select
                      id="accom"
                      value={accomTier}
                      onChange={(e) => setAccomTier(e.target.value as AccommodationTier)}
                      className={fieldClass()}
                    >
                      {ACCOM_TIERS.map((t) => (
                        <option key={t} value={t} className="bg-navy">
                          {t[0].toUpperCase() + t.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="food" className={labelClass()}>Food style</label>
                    <select
                      id="food"
                      value={foodProfile}
                      onChange={(e) => setFoodProfile(e.target.value as FoodProfile)}
                      className={fieldClass()}
                    >
                      {FOOD_PROFILES.map((f) => (
                        <option key={f} value={f} className="bg-navy">
                          {f[0].toUpperCase() + f.slice(1)}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <p className={labelClass()}>Transfer types you'll accept</p>
                  <div className="flex flex-wrap gap-2">
                    {TRANSFER_MODES.map(({ value, label }) => {
                      const active = transferModes.has(value);
                      return (
                        <button
                          type="button"
                          key={value}
                          onClick={() => toggleTransferMode(value)}
                          className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                            active
                              ? "border-sky bg-sky/15 text-sky"
                              : "border-white/15 text-ice/60 hover:border-white/30"
                          }`}
                        >
                          {label}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1 text-[11px] text-ice/40">None selected = no preference.</p>
                </div>

                <div>
                  <label htmlFor="connections" className={labelClass()}>Maximum flight connections</label>
                  <select
                    id="connections"
                    value={maxConnections}
                    onChange={(e) => setMaxConnections(e.target.value)}
                    className={fieldClass()}
                  >
                    <option value="" className="bg-navy">No preference</option>
                    <option value="0" className="bg-navy">Nonstop only</option>
                    <option value="1" className="bg-navy">Up to 1 stop</option>
                    <option value="2" className="bg-navy">Up to 2 stops</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2.5 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-signal py-3.5 font-semibold text-white shadow-lg shadow-signal/20 transition-colors hover:bg-signal/90 disabled:opacity-50"
          >
            {loading ? "Searching…" : mode === "fixed" ? "Find my trip" : "Find me a deal"}
          </button>
        </form>
      </div>
    </section>
  );
}
