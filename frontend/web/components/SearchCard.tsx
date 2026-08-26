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
import { todayPlusDays, addDays } from "@/lib/format";
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
import { TripStylePresets, TRIP_STYLES, type TripStyle, type TripStyleId } from "./TripStylePresets";

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
  return "w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm text-ink outline-none focus:border-sky focus:ring-1 focus:ring-sky";
}
function labelClass() {
  return "mb-1.5 block text-xs font-semibold uppercase tracking-wide text-subtle";
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

  // One unified date range: if latest - earliest == nights away, this is
  // effectively "exact dates" (a single candidate start date); wider than
  // that, the backend searches every valid start date in between. See
  // lib/api.searchFlexibleWindow -- there's no separate "fixed date" mode
  // in this UI any more, the search itself degrades to one date naturally.
  const [earliest, setEarliest] = useState(todayPlusDays(30));
  const [latest, setLatest] = useState(todayPlusDays(37));
  // Full days on the mountain -- what the user actually cares about, not
  // nights away (see lib/api.FixedDateSearchParams.ski_days). Nights
  // away is always skiDays + 1 (arrive the evening before day 1, leave
  // the day after the last ski day) -- see the `nights` derivation
  // wherever it's used below.
  const [skiDays, setSkiDays] = useState(6);
  const [startWeekday, setStartWeekday] = useState<WeekdayName | "">("");

  const [resortNames, setResortNames] = useState<string[]>([]);
  const [selectedResorts, setSelectedResorts] = useState<Set<string>>(new Set());
  const [resortMode, setResortMode] = useState<ResortFilterMode>("include");

  const [travellers, setTravellers] = useState(2);
  const [skillLevel, setSkillLevel] = useState<SkillLevel>("intermediate");
  const [budget, setBudget] = useState(1500);
  const [weights, setWeights] = useState<RawWeights>(DEFAULT_RAW_WEIGHTS);
  // Which one-tap trip style is currently applied, or null once the
  // user hand-edits a slider (at which point no preset describes their
  // weights any more and claiming one would be a lie).
  const [styleId, setStyleId] = useState<TripStyleId | null>("balanced");
  const [slidersOpen, setSlidersOpen] = useState(false);

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

  // If the user pushes the earliest date past the current latest date
  // (or so close that the window can no longer fit a trip of this
  // length), the form used to just show a validation error on submit --
  // annoying when it's obvious what they meant. Auto-carry the latest
  // date forward instead, keeping it a window at least `nights` long.
  function handleEarliestChange(value: string) {
    setEarliest(value);
    const nights = skiDays + 1;
    if (value && latest < addDays(value, nights)) {
      setLatest(addDays(value, nights));
    }
  }

  // One tap sets all six weights AND the accommodation/food tiers that
  // go with that intent -- the whole point is that picking a style
  // answers questions the user would otherwise face one by one.
  function applyStyle(style: TripStyle) {
    setStyleId(style.id);
    setWeights(style.weights);
    setAccomTier(style.accommodationTier);
    setFoodProfile(style.foodProfile);
  }

  function handleWeightsChange(next: RawWeights) {
    setWeights(next);
    // Hand-editing means the result no longer matches any preset.
    const match = TRIP_STYLES.find(
      (st) => (Object.keys(next) as (keyof RawWeights)[]).every((k) => st.weights[k] === next[k])
    );
    setStyleId(match ? match.id : null);
  }

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

    if (!(skiDays > 0)) {
      setError(t("errorTripLength"));
      return;
    }
    const nights = skiDays + 1;
    const windowNights = Math.round(
      (new Date(latest).getTime() - new Date(earliest).getTime()) / 86_400_000
    );
    if (windowNights < nights) {
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
          ski_days: skiDays,
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
      <div className="rounded-2xl border border-line bg-surface p-6 sm:p-8">
        <form id="ski-search-form" onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className={labelClass()}>{t("departureCity")}</label>
            <input value="Tel Aviv (TLV)" disabled className={`${fieldClass()} opacity-60`} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="earliest" className={labelClass()}>{t("earliestDate")}</label>
              <input
                id="earliest" type="date" value={earliest}
                onChange={(e) => handleEarliestChange(e.target.value)}
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
              <label htmlFor="skiDays" className={labelClass()}>{t("skiDaysLabel")}</label>
              <input
                id="skiDays" type="number" min={1} max={30} value={skiDays}
                onChange={(e) => setSkiDays(Number(e.target.value))}
                className={fieldClass()} required
              />
              <p className="mt-1 text-[11px] text-subtle">
                {t("skiDaysHint", { nights: skiDays + 1 })}
              </p>
            </div>
            <div>
              <label htmlFor="weekday" className={labelClass()}>{t("startDayOfWeek")}</label>
              <select
                id="weekday" value={startWeekday}
                onChange={(e) => setStartWeekday(e.target.value as WeekdayName | "")}
                className={fieldClass()}
              >
                <option value="" className="bg-canvas">{t("anyDay")}</option>
                {WEEKDAYS.map(({ value, key }) => (
                  <option key={value} value={value} className="bg-canvas">{t(key)}</option>
                ))}
              </select>
            </div>
          </div>
          <p className="-mt-3 text-[11px] text-subtle">{t("rangeHint")}</p>

          <ResortPicker
            resortNames={resortNames}
            selected={selectedResorts}
            onToggle={toggleResort}
            isSignedIn={Boolean(accessToken)}
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
                  <option key={value} value={value} className="bg-canvas">{t(key)}</option>
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

          <TripStylePresets activeId={styleId} onPick={applyStyle} />

          <div className="rounded-xl border border-line bg-sunken/60 p-3">
            <button
              type="button"
              onClick={() => setSlidersOpen((o) => !o)}
              className="flex w-full items-center justify-between text-sm font-semibold text-sky hover:text-sky/80"
              aria-expanded={slidersOpen}
            >
              <span>{slidersOpen ? t("hideFineTune") : t("fineTune")}</span>
              <span className="text-xs font-medium text-subtle">
                {styleId ? t(TRIP_STYLES.find((s2) => s2.id === styleId)!.labelKey) : t("styleCustom")}
              </span>
            </button>
            {slidersOpen && (
              <div className="mt-4">
                <p className="mb-3 text-xs text-subtle">{t("fineTuneHint")}</p>
                <PrioritySliders value={weights} onChange={handleWeightsChange} />
              </div>
            )}
          </div>

          <div className="border-t border-line pt-4">
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
                        <option key={value} value={value} className="bg-canvas">{t(key)}</option>
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
                        <option key={value} value={value} className="bg-canvas">{t(key)}</option>
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
                            active ? "border-sky bg-sky/15 text-sky" : "border-line text-subtle hover:border-line-strong"
                          }`}
                        >
                          {t(key)}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1 text-[11px] text-subtle">{t("transferNonePreference")}</p>
                </div>

                <div>
                  <label htmlFor="connections" className={labelClass()}>{t("maxFlightConnections")}</label>
                  <select
                    id="connections" value={maxConnections}
                    onChange={(e) => setMaxConnections(e.target.value)}
                    className={fieldClass()}
                  >
                    <option value="" className="bg-canvas">{t("connectionsNoPreference")}</option>
                    <option value="0" className="bg-canvas">{t("connectionsNonstop")}</option>
                    <option value="1" className="bg-canvas">{t("connectionsUpTo1")}</option>
                    <option value="2" className="bg-canvas">{t("connectionsUpTo2")}</option>
                  </select>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-warn-soft border border-warn/30 px-3 py-2.5 text-sm text-warn">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-signal py-3.5 font-semibold text-white shadow-lg shadow-signal/25 transition-colors hover:bg-signal/90 disabled:opacity-50"
          >
            {loading ? t("searching") : t("findMyTrip")}
          </button>
        </form>
      </div>
      <StickySubmitBar formId="ski-search-form" loading={loading} />
    </section>
  );
}

/**
 * A mobile-only sticky submit bar.
 *
 * The form is long -- dates, trip length, resorts, travellers, skill,
 * budget, style, and optional preferences. On a phone that means the
 * real submit button spends most of the session off-screen, so anyone
 * who scrolls up to change one field has to hunt back down to act on
 * it. This keeps the action permanently reachable with a thumb.
 *
 * It appears only once the form has been scrolled into view, so it
 * never covers the hero, and hides again once the real button is
 * visible -- two identical buttons on screen at once looks like a bug.
 */
export function StickySubmitBar({
  formId,
  loading,
}: {
  formId: string;
  loading: boolean;
}) {
  const { t } = useTranslation();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const form = document.getElementById(formId);
    const realButton = form?.querySelector('button[type="submit"]');
    if (!form || !realButton) return;

    let formInView = false;
    let buttonInView = false;
    const sync = () => setVisible(formInView && !buttonInView);

    const formObserver = new IntersectionObserver(
      ([e]) => {
        formInView = e.isIntersecting;
        sync();
      },
      { rootMargin: "-80px 0px 0px 0px" }
    );
    const buttonObserver = new IntersectionObserver(([e]) => {
      buttonInView = e.isIntersecting;
      sync();
    });
    formObserver.observe(form);
    buttonObserver.observe(realButton);
    return () => {
      formObserver.disconnect();
      buttonObserver.disconnect();
    };
  }, [formId]);

  if (!visible) return null;
  return (
    <div className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-surface/95 p-3 backdrop-blur-sm sm:hidden">
      <button
        type="submit"
        form={formId}
        disabled={loading}
        className="w-full rounded-xl bg-signal py-3.5 font-semibold text-white shadow-lg shadow-signal/25 transition-colors hover:bg-signal/90 disabled:opacity-50"
      >
        {loading ? t("searching") : t("findMyTrip")}
      </button>
    </div>
  );
}
