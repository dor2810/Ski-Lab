"use client";

import { useEffect, useState } from "react";
import {
  searchFlexibleWindow,
  listResortNames,
  ApiError,
  type SkillLevel,
  type AccommodationTier,
  type FoodProfile,
  type TransferMode,
  type WeekdayName,
  type TripResult,
} from "@/lib/api";
import { todayPlusDays } from "@/lib/format";
import {
  PrioritySliders,
  DEFAULT_RAW_WEIGHTS,
  normalizeWeights,
  type RawWeights,
} from "./PrioritySliders";
import { ResortPicker, type ResortFilterMode } from "./ResortPicker";

export interface SearchOutcome {
  results: TripResult[];
  livePricingActive: boolean;
  candidateDates: number;
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
const WEEKDAYS: { value: WeekdayName; label: string }[] = [
  { value: "monday", label: "Monday" },
  { value: "tuesday", label: "Tuesday" },
  { value: "wednesday", label: "Wednesday" },
  { value: "thursday", label: "Thursday" },
  { value: "friday", label: "Friday" },
  { value: "saturday", label: "Saturday" },
  { value: "sunday", label: "Sunday" },
];

function fieldClass() {
  return "w-full rounded-lg border border-white/15 bg-navy px-3 py-2.5 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky";
}
function labelClass() {
  return "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-ice/60";
}

export function SearchCard({
  onOutcome,
  onSearchStart,
}: {
  onOutcome: (outcome: SearchOutcome) => void;
  onSearchStart: () => void;
}) {
  // One unified date range: if latest - earliest == trip_nights, this is
  // effectively "exact dates" (a single candidate start date); wider than
  // that, the backend searches every valid start date in between. See
  // lib/api.searchFlexibleWindow -- there's no separate "fixed date" mode
  // in this UI any more, the search itself degrades to one date naturally.
  const [earliest, setEarliest] = useState(todayPlusDays(30));
  const [latest, setLatest] = useState(todayPlusDays(37));
  const [tripNights, setTripNights] = useState(6);
  const [startWeekday, setStartWeekday] = useState<WeekdayName | "">("");

  const [resortNames, setResortNames] = useState<string[]>([]);
  const [selectedResorts, setSelectedResorts] = useState<Set<string>>(new Set());
  const [resortMode, setResortMode] = useState<ResortFilterMode>("include");

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

  useEffect(() => {
    listResortNames().then(setResortNames).catch(() => {
      /* resort picker just stays empty/loading -- not fatal to the rest of the form */
    });
  }, []);

  function toggleResort(name: string) {
    setSelectedResorts((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });
  }

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

    if (!(tripNights > 0)) {
      setError("Trip length must be at least 1 night.");
      return;
    }
    const windowNights = Math.round(
      (new Date(latest).getTime() - new Date(earliest).getTime()) / 86_400_000
    );
    if (windowNights < tripNights) {
      setError("The date range must be at least as long as the trip.");
      return;
    }

    const resortList = selectedResorts.size > 0 ? [...selectedResorts] : null;

    setLoading(true);
    onSearchStart();
    try {
      const data = await searchFlexibleWindow({
        budget_eur_per_person: budget,
        group_size: travellers,
        skill_level: skillLevel,
        accommodation_tier: accomTier,
        food_profile: foodProfile,
        equipment_tier: "standard",
        max_connections: maxConnections === "" ? null : Number(maxConnections),
        preferred_transfer_modes: transferModes.size > 0 ? [...transferModes] : null,
        include_resorts: resortMode === "include" ? resortList : null,
        exclude_resorts: resortMode === "exclude" ? resortList : null,
        start_weekday: startWeekday === "" ? null : startWeekday,
        weights: normalizeWeights(weights),
        trip_nights: tripNights,
        earliest_date: earliest,
        latest_date: latest,
        top_n: 12,
      });
      onOutcome({
        results: data.results,
        livePricingActive: data.live_pricing_active,
        candidateDates: data.candidate_dates_per_resort,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="search" className="mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-white/10 bg-midnight p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className={labelClass()}>Departure city</label>
            <input value="Tel Aviv (TLV)" disabled className={`${fieldClass()} opacity-60`} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="earliest" className={labelClass()}>Earliest date</label>
              <input
                id="earliest" type="date" value={earliest}
                onChange={(e) => setEarliest(e.target.value)}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="latest" className={labelClass()}>Latest return</label>
              <input
                id="latest" type="date" value={latest}
                onChange={(e) => setLatest(e.target.value)}
                className={fieldClass()} required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="nights" className={labelClass()}>Trip length (nights)</label>
              <input
                id="nights" type="number" min={1} max={30} value={tripNights}
                onChange={(e) => setTripNights(Number(e.target.value))}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="weekday" className={labelClass()}>Start day of week</label>
              <select
                id="weekday" value={startWeekday}
                onChange={(e) => setStartWeekday(e.target.value as WeekdayName | "")}
                className={fieldClass()}
              >
                <option value="" className="bg-navy">Any day</option>
                {WEEKDAYS.map(({ value, label }) => (
                  <option key={value} value={value} className="bg-navy">{label}</option>
                ))}
              </select>
            </div>
          </div>
          <p className="-mt-3 text-[11px] text-ice/40">
            Give a wider date range than your trip length and we&rsquo;ll search every valid start
            date in it (e.g. only Saturdays, if set above) for the best deal.
          </p>

          <ResortPicker
            resortNames={resortNames}
            selected={selectedResorts}
            onToggle={toggleResort}
            mode={resortMode}
            onModeChange={setResortMode}
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="travellers" className={labelClass()}>Travellers</label>
              <input
                id="travellers" type="number" min={1} max={20} value={travellers}
                onChange={(e) => setTravellers(Number(e.target.value))}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="skill" className={labelClass()}>Skill level</label>
              <select
                id="skill" value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                className={fieldClass()}
              >
                {SKILL_LEVELS.map((s) => (
                  <option key={s} value={s} className="bg-navy">{s[0].toUpperCase() + s.slice(1)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="budget" className={labelClass()}>Budget per person (EUR)</label>
            <input
              id="budget" type="number" min={1} value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className={fieldClass()} required
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
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="accom" className={labelClass()}>Accommodation tier</label>
                    <select
                      id="accom" value={accomTier}
                      onChange={(e) => setAccomTier(e.target.value as AccommodationTier)}
                      className={fieldClass()}
                    >
                      {ACCOM_TIERS.map((t) => (
                        <option key={t} value={t} className="bg-navy">{t[0].toUpperCase() + t.slice(1)}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="food" className={labelClass()}>Food style</label>
                    <select
                      id="food" value={foodProfile}
                      onChange={(e) => setFoodProfile(e.target.value as FoodProfile)}
                      className={fieldClass()}
                    >
                      {FOOD_PROFILES.map((f) => (
                        <option key={f} value={f} className="bg-navy">{f[0].toUpperCase() + f.slice(1)}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <p className={labelClass()}>Transfer types you&apos;ll accept</p>
                  <div className="flex flex-wrap gap-2">
                    {TRANSFER_MODES.map(({ value, label }) => {
                      const active = transferModes.has(value);
                      return (
                        <button
                          type="button" key={value}
                          onClick={() => toggleTransferMode(value)}
                          className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                            active ? "border-sky bg-sky/15 text-sky" : "border-white/15 text-ice/60 hover:border-white/30"
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
                    id="connections" value={maxConnections}
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
            {loading ? "Searching…" : "Find my trip"}
          </button>
        </form>
      </div>
    </section>
  );
}
