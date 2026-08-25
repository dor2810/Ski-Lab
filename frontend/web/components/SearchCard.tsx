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
import { useAuth } from "@/lib/auth/context";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
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

const SKILL_LEVELS: { value: SkillLevel; key: keyof Dictionary }[] = [
  { value: "beginner", key: "skillBeginner" },
  { value: "intermediate", key: "skillIntermediate" },
  { value: "advanced", key: "skillAdvanced" },
  { value: "expert", key: "skillExpert" },
];
const ACCOM_TIERS: { value: AccommodationTier; key: keyof Dictionary }[] = [
  { value: "budget", key: "tierBudget" },
  { value: "standard", key: "tierStandard" },
  { value: "luxury", key: "tierLuxury" },
];
const FOOD_PROFILES: { value: FoodProfile; key: keyof Dictionary }[] = [
  { value: "budget", key: "foodBudget" },
  { value: "normal", key: "foodNormal" },
  { value: "luxury", key: "foodLuxury" },
];
const TRANSFER_MODES: { value: TransferMode; key: keyof Dictionary }[] = [
  { value: "shared_shuttle", key: "transferSharedShuttle" },
  { value: "private_transfer", key: "transferPrivateTransfer" },
  { value: "train", key: "transferTrain" },
  { value: "bus", key: "transferBus" },
];
const WEEKDAYS: { value: WeekdayName; key: keyof Dictionary }[] = [
  { value: "monday", key: "weekdayMonday" },
  { value: "tuesday", key: "weekdayTuesday" },
  { value: "wednesday", key: "weekdayWednesday" },
  { value: "thursday", key: "weekdayThursday" },
  { value: "friday", key: "weekdayFriday" },
  { value: "saturday", key: "weekdaySaturday" },
  { value: "sunday", key: "weekdaySunday" },
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
  const { t } = useTranslation();
  const { accessToken } = useAuth();

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
    if (!accessToken) return;
    listResortNames(accessToken).then(setResortNames).catch(() => {
      /* resort picker just stays empty/loading -- not fatal to the rest of the form */
    });
  }, [accessToken]);

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

    if (!accessToken) {
      setError(t("signInToSearch"));
      return;
    }

    if (!(tripNights > 0)) {
      setError(t("errorTripLength"));
      return;
    }
    const windowNights = Math.round(
      (new Date(latest).getTime() - new Date(earliest).getTime()) / 86_400_000
    );
    if (windowNights < tripNights) {
      setError(t("errorRangeTooShort"));
      return;
    }

    const resortList = selectedResorts.size > 0 ? [...selectedResorts] : null;

    setLoading(true);
    onSearchStart();
    try {
      const data = await searchFlexibleWindow(
        {
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
        },
        accessToken
      );
      onOutcome({
        results: data.results,
        livePricingActive: data.live_pricing_active,
        candidateDates: data.candidate_dates_per_resort,
      });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("errorGeneric"));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="search" className="mx-auto max-w-3xl px-6 py-16">
      <div className="rounded-2xl border border-white/10 bg-midnight p-6 sm:p-8">
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className={labelClass()}>{t("departureCity")}</label>
            <input value="Tel Aviv (TLV)" disabled className={`${fieldClass()} opacity-60`} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="earliest" className={labelClass()}>{t("earliestDate")}</label>
              <input
                id="earliest" type="date" value={earliest}
                onChange={(e) => setEarliest(e.target.value)}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="latest" className={labelClass()}>{t("latestReturn")}</label>
              <input
                id="latest" type="date" value={latest}
                onChange={(e) => setLatest(e.target.value)}
                className={fieldClass()} required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="nights" className={labelClass()}>{t("tripLengthNights")}</label>
              <input
                id="nights" type="number" min={1} max={30} value={tripNights}
                onChange={(e) => setTripNights(Number(e.target.value))}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="weekday" className={labelClass()}>{t("startDayOfWeek")}</label>
              <select
                id="weekday" value={startWeekday}
                onChange={(e) => setStartWeekday(e.target.value as WeekdayName | "")}
                className={fieldClass()}
              >
                <option value="" className="bg-navy">{t("anyDay")}</option>
                {WEEKDAYS.map(({ value, key }) => (
                  <option key={value} value={value} className="bg-navy">{t(key)}</option>
                ))}
              </select>
            </div>
          </div>
          <p className="-mt-3 text-[11px] text-ice/40">{t("rangeHint")}</p>

          <ResortPicker
            resortNames={resortNames}
            selected={selectedResorts}
            onToggle={toggleResort}
            mode={resortMode}
            onModeChange={setResortMode}
          />

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="travellers" className={labelClass()}>{t("travellers")}</label>
              <input
                id="travellers" type="number" min={1} max={20} value={travellers}
                onChange={(e) => setTravellers(Number(e.target.value))}
                className={fieldClass()} required
              />
            </div>
            <div>
              <label htmlFor="skill" className={labelClass()}>{t("skillLevel")}</label>
              <select
                id="skill" value={skillLevel}
                onChange={(e) => setSkillLevel(e.target.value as SkillLevel)}
                className={fieldClass()}
              >
                {SKILL_LEVELS.map(({ value, key }) => (
                  <option key={value} value={value} className="bg-navy">{t(key)}</option>
                ))}
              </select>
            </div>
          </div>

          <div>
            <label htmlFor="budget" className={labelClass()}>{t("budgetPerPerson")}</label>
            <input
              id="budget" type="number" min={1} value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className={fieldClass()} required
            />
          </div>

          <div>
            <p className={labelClass()}>{t("priorities")}</p>
            <PrioritySliders value={weights} onChange={setWeights} />
          </div>

          <div className="border-t border-white/10 pt-4">
            <button
              type="button"
              onClick={() => setPrefsOpen((o) => !o)}
              className="text-sm font-semibold text-sky hover:text-sky/80"
            >
              {prefsOpen ? t("hideOptionalPreferences") : t("optionalPreferences")}
            </button>

            {prefsOpen && (
              <div className="mt-4 space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor="accom" className={labelClass()}>{t("accommodationTier")}</label>
                    <select
                      id="accom" value={accomTier}
                      onChange={(e) => setAccomTier(e.target.value as AccommodationTier)}
                      className={fieldClass()}
                    >
                      {ACCOM_TIERS.map(({ value, key }) => (
                        <option key={value} value={value} className="bg-navy">{t(key)}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label htmlFor="food" className={labelClass()}>{t("foodStyle")}</label>
                    <select
                      id="food" value={foodProfile}
                      onChange={(e) => setFoodProfile(e.target.value as FoodProfile)}
                      className={fieldClass()}
                    >
                      {FOOD_PROFILES.map(({ value, key }) => (
                        <option key={value} value={value} className="bg-navy">{t(key)}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div>
                  <p className={labelClass()}>{t("transferTypesAccept")}</p>
                  <div className="flex flex-wrap gap-2">
                    {TRANSFER_MODES.map(({ value, key }) => {
                      const active = transferModes.has(value);
                      return (
                        <button
                          type="button" key={value}
                          onClick={() => toggleTransferMode(value)}
                          className={`rounded-full border px-3 py-1.5 text-xs font-semibold transition-colors ${
                            active ? "border-sky bg-sky/15 text-sky" : "border-white/15 text-ice/60 hover:border-white/30"
                          }`}
                        >
                          {t(key)}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1 text-[11px] text-ice/40">{t("transferNonePreference")}</p>
                </div>

                <div>
                  <label htmlFor="connections" className={labelClass()}>{t("maxFlightConnections")}</label>
                  <select
                    id="connections" value={maxConnections}
                    onChange={(e) => setMaxConnections(e.target.value)}
                    className={fieldClass()}
                  >
                    <option value="" className="bg-navy">{t("connectionsNoPreference")}</option>
                    <option value="0" className="bg-navy">{t("connectionsNonstop")}</option>
                    <option value="1" className="bg-navy">{t("connectionsUpTo1")}</option>
                    <option value="2" className="bg-navy">{t("connectionsUpTo2")}</option>
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
            {loading ? t("searching") : t("findMyTrip")}
          </button>
        </form>
      </div>
    </section>
  );
}
