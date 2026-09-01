"use client";

import { useEffect, useState } from "react";
import {
  searchFlexibleWindow,
  listResortNames,
  listPopularResortNames,
  getSearchCredits,
  ApiError,
  type SkillLevel,
  type AccommodationTier,
  type FoodProfile,
  type TransferMode,
  type WeekdayName,
  type TripResult,
  type Credits,
  type DatePrice,
  type FixedDateSearchParams,
} from "@/lib/api";
import { todayPlusDays, addDays } from "@/lib/format";
import { useAuth, SessionExpiredError } from "@/lib/auth/context";
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
import { CreditMeter } from "./CreditMeter";

export interface SearchOutcome {
  results: TripResult[];
  /**
   * Every (resort, start date) the search evaluated -- the calendar's
   * data. `results` is the capped best-trips list: a December search
   * evaluated 24 start dates and returned 3, so drawing a calendar
   * from it left priced days blank. Absent for fixed-date searches,
   * which have a single date by definition.
   */
  datePrices?: DatePrice[];
  /**
   * The preferences THIS search ran with, so a single (resort, date)
   * can be re-priced later without the traveller re-filling the form.
   * Used by the calendar's "get the real price" action, which spends a
   * credit on one day.
   */
  refineParams?: FixedDateSearchParams;
  livePricingActive: boolean;
  // See lib/api.ts's SearchResponse.live_pricing_blocked.
  livePricingBlocked: boolean;
  candidateDates: number;
  // The max-connections preference THIS search ran with. The booking-
  // link endpoint re-runs the same flight query at click time, and a
  // different connections cap is a different query that may not
  // contain the clicked itinerary.
  maxConnections: number | null;
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
  // First, because it is the one most people actually want: Saturday
  // is the classic package-changeover day, Sunday the established
  // cheaper alternative -- "weekend" searches both.
  { value: "weekend", key: "weekdayWeekend" },
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
  const { accessToken, runAuthed } = useAuth();

  // One unified date range: if latest - earliest == nights away, this is
  // effectively "exact dates" (a single candidate start date); wider than
  // that, the backend searches every valid start date in between. See
  // lib/api.searchFlexibleWindow -- there's no separate "fixed date" mode
  // in this UI any more, the search itself degrades to one date naturally.
  // Ski season starts December 1st (the backend floors earlier dates
  // to it anyway) -- default the form INTO the season instead of
  // showing an autumn window the server would silently reshape.
  const seasonFloor = (() => {
    const now = new Date();
    if (now.getMonth() + 1 >= 5 && now.getMonth() + 1 <= 11) {
      return `${now.getFullYear()}-12-01`;
    }
    return todayPlusDays(1);
  })();
  const defaultEarliest = todayPlusDays(30) > seasonFloor ? todayPlusDays(30) : seasonFloor;
  const [earliest, setEarliest] = useState(defaultEarliest);
  const [latest, setLatest] = useState(addDays(defaultEarliest, 7));
  // Full days on the mountain -- what the user actually cares about, not
  // nights away (see lib/api.FixedDateSearchParams.ski_days). Nights
  // away is always skiDays + 1 (arrive the evening before day 1, leave
  // the day after the last ski day) -- see the `nights` derivation
  // wherever it's used below.
  const [skiDays, setSkiDays] = useState(6);
  const [startWeekday, setStartWeekday] = useState<WeekdayName | "">("");

  // The picker shows the curated shortlist by default and the full set
  // on request. Both are held so toggling doesn't refetch, and so the
  // shortlist is available to scope a search that has no explicit
  // selection (see handleSubmit).
  const [mainstreamNames, setMainstreamNames] = useState<string[]>([]);
  const [allNames, setAllNames] = useState<string[]>([]);
  const [showAllResorts, setShowAllResorts] = useState(false);
  const [popularNames, setPopularNames] = useState<string[]>([]);
  const resortNames = showAllResorts ? allNames : mainstreamNames;
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
  // WHICH property the trip gets priced on. Empty string = no limit,
  // which must send null rather than 0 -- a EUR0 cap matches nothing.
  const [accomMaxPP, setAccomMaxPP] = useState<string>("");
  const [accomMinStars, setAccomMinStars] = useState<string>("");
  // Guest score, not stars. Far better covered: a live Kitzbuehel
  // search returned review scores for 11 of 12 properties and star
  // classes for NONE of them (checked 2026-08-30).
  const [accomMinRating, setAccomMinRating] = useState<string>("");
  const [accomMinReviews, setAccomMinReviews] = useState<string>("");
  // Real metres to the nearest lift, computed from coordinates against
  // OpenStreetMap -- the one filter that is actually about skiing.
  const [accomMaxLiftKm, setAccomMaxLiftKm] = useState<string>("");
  const [accomPropertyType, setAccomPropertyType] = useState<string>("HOTELS");
  const [foodProfile, setFoodProfile] = useState<FoodProfile>("normal");
  const [transferModes, setTransferModes] = useState<Set<TransferMode>>(new Set());
  const [maxConnections, setMaxConnections] = useState<string>(""); // "" = no preference
  // Bringing your own skis/board changes which transfer VEHICLES the
  // operator offers at all (with bags: minivans only; without: a
  // cheaper small car), so it changes the real transfer price -- not a
  // cosmetic preference. Defaults to true: this is a ski product, and
  // assuming gear is the safe error.
  const [withSkiBags, setWithSkiBags] = useState(true);

  const [credits, setCredits] = useState<Credits | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!accessToken) return;
    runAuthed((token) => getSearchCredits(token)).then(setCredits).catch(() => {
      /* the meter just stays hidden -- never block the form over it */
    });
    runAuthed((token) => listResortNames(token, true)).then(setMainstreamNames).catch(() => {
      /* resort picker just stays empty/loading -- not fatal to the rest of the form */
    });
    runAuthed((token) => listResortNames(token)).then(setAllNames).catch(() => {
      /* only needed if the user asks to see everything */
    });
    runAuthed((token) => listPopularResortNames(token)).then(setPopularNames).catch(() => {
      /* the one-tap button just doesn't render -- never blocks the form */
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
    // A style changes what gets SEARCHED, not just how it's ranked.
    // The connections dropdown updates visibly rather than silently, so
    // the user can see what the style did and override it.
    setMaxConnections(style.maxConnections === null ? "" : String(style.maxConnections));
  }

  // Mirrors engine/date_search.candidate_start_dates + api/credits.py's
  // cost rule, so the quoted price matches what the server charges. If
  // those ever disagree the user sees one number and pays another, so
  // this deliberately reproduces the rule rather than approximating it.
  const pendingCost = (() => {
    const nights = skiDays + 1;
    const windowDays = Math.round(
      (new Date(latest).getTime() - new Date(earliest).getTime()) / 86_400_000
    );
    if (!Number.isFinite(windowDays) || windowDays < nights) return null;
    let candidates = windowDays - nights + 1;
    if (startWeekday !== "") candidates = Math.ceil(candidates / 7);
    return Math.max(1, Math.min(60, candidates));
  })();

  function handleWeightsChange(next: RawWeights) {
    setWeights(next);
    // Hand-editing means the result no longer matches any preset.
    const match = TRIP_STYLES.find(
      (st) => (Object.keys(next) as (keyof RawWeights)[]).every((k) => st.weights[k] === next[k])
    );
    setStyleId(match ? match.id : null);
  }

  // One tap selects the whole curated set; tapping again clears it, so
  // the action is undoable without hunting down ten individual chips.
  function togglePopularSelection() {
    const allSelected = popularNames.length > 0 && popularNames.every((n) => selectedResorts.has(n));
    setSelectedResorts((prev) => {
      const next = new Set(prev);
      for (const name of popularNames) {
        if (allSelected) next.delete(name);
        else next.add(name);
      }
      return next;
    });
    // Picking a set of resorts to INCLUDE is what this button means; if
    // the picker was flipped to "except these" the same tap would
    // silently exclude them, which is the opposite of what it says.
    if (!allSelected) setResortMode("include");
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

    // The original complaint was about RESULTS, not just the picker: with
    // nothing selected this sent include_resorts=null, so the engine
    // ranked all 37 and obscure resorts surfaced. Default the search to
    // the same shortlist the picker shows. Explicitly choosing "show
    // all" opts back into the full set, so nothing is unreachable.
    const selectedList = selectedResorts.size > 0 ? [...selectedResorts] : null;
    const defaultScope = showAllResorts || mainstreamNames.length === 0 ? null : mainstreamNames;
    const resortList = selectedList ?? defaultScope;
    const effectiveMode: ResortFilterMode = selectedList ? resortMode : "include";

    // Built once and reused: the flexible search sends it now, and the
    // calendar's "get the real price for this day" action re-sends the
    // SAME preferences for one date later. Rebuilding it there would be
    // a second place for the two to drift apart.
    const common = {
          budget_eur_per_person: budget,
          group_size: travellers,
          skill_level: skillLevel,
          accommodation_tier: accomTier,
          accommodation_max_eur_per_person: accomMaxPP.trim() === "" ? null : Number(accomMaxPP),
          accommodation_min_star_class: accomMinStars === "" ? null : Number(accomMinStars),
          accommodation_min_rating: accomMinRating === "" ? null : Number(accomMinRating),
          accommodation_min_review_count: accomMinReviews === "" ? null : Number(accomMinReviews),
          accommodation_max_distance_to_lifts_km:
            accomMaxLiftKm === "" ? null : Number(accomMaxLiftKm),
          accommodation_property_type: accomPropertyType,
          food_profile: foodProfile,
          equipment_tier: "standard" as const,
          max_connections: maxConnections === "" ? null : Number(maxConnections),
          with_ski_bags: withSkiBags,
          preferred_transfer_modes: transferModes.size > 0 ? [...transferModes] : null,
          include_resorts: effectiveMode === "include" ? resortList : null,
          exclude_resorts: effectiveMode === "exclude" ? resortList : null,
          start_weekday: startWeekday === "" ? null : startWeekday,
          weights: normalizeWeights(weights),
          ski_days: skiDays,
    };

    setLoading(true);
    onSearchStart();
    try {
      const data = await runAuthed((token) => searchFlexibleWindow(
        {
          ...common,
          earliest_date: earliest,
          latest_date: latest,
          // 24 rows, 6 per resort. FREE: the engine evaluates every
          // (resort, date) whatever this says -- 192 pairs on a
          // December window, measured identical at top_n 10 and 40 --
          // and it already live-prices up to 24 pairs (_LIVE_REPRICE_N)
          // chosen with this very per-resort cap. At 12 we were paying
          // to price 24 and showing 12. Six per resort rather than
          // three because that is what widens the DATES shown, which
          // is what the calendar above is asking about.
          top_n: 24,
          max_results_per_resort: 6,
        },
        token
      ));
      if (data.credits) setCredits(data.credits);
      onOutcome({
        results: data.results,
        // The same preferences, ready to re-run for a single day.
        refineParams: common,
        // Only the date-range search has a grid of dates to report.
        datePrices: "date_prices" in data ? data.date_prices : undefined,
        livePricingActive: data.live_pricing_active,
        livePricingBlocked: data.live_pricing_blocked,
        candidateDates: data.candidate_dates_per_resort,
        maxConnections: maxConnections === "" ? null : Number(maxConnections),
      });
    } catch (err) {
      // A dead session is not a search failure -- say so plainly and
      // point at the fix, instead of surfacing a raw "Not authenticated".
      if (err instanceof SessionExpiredError) {
        setError(t("sessionExpired"));
      } else {
        setError(err instanceof ApiError ? err.message : t("errorGeneric"));
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section id="search" className="mx-auto max-w-3xl px-4 py-10 sm:px-6 sm:py-16">
      <div className="rounded-2xl border border-line bg-surface p-4 sm:p-8">
        <form id="ski-search-form" onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label className={labelClass()}>{t("departureCity")}</label>
            <input value="Tel Aviv (TLV)" disabled className={`${fieldClass()} opacity-60`} />
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div>
              <label htmlFor="earliest" className={labelClass()}>{t("earliestDate")}</label>
              <input
                id="earliest" type="date" min={seasonFloor} value={earliest}
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
              {/* Research-sourced guidance, shown once a day is being
                  chosen: Sat = classic changeover, Sun = cheaper,
                  midweek = cheapest. */}
              {startWeekday !== "" && (
                <p className="mt-1 text-[11px] leading-snug text-subtle">{t("weekdayHint")}</p>
              )}
            </div>
          </div>
          <p className="-mt-3 text-[11px] text-subtle">{t("rangeHint")}</p>

          <ResortPicker
            resortNames={resortNames}
            selected={selectedResorts}
            onToggle={toggleResort}
            isSignedIn={Boolean(accessToken)}
            showingAll={showAllResorts}
            onToggleShowAll={() => setShowAllResorts((v) => !v)}
            hiddenCount={Math.max(0, allNames.length - mainstreamNames.length)}
            popularNames={popularNames}
            onSelectPopular={togglePopularSelection}
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
                    <label htmlFor="accomMax" className={labelClass()}>
                      {t("accommodationMaxLabel")}
                    </label>
                    <input
                      id="accomMax"
                      type="number"
                      min={0}
                      step={25}
                      inputMode="numeric"
                      value={accomMaxPP}
                      onChange={(e) => setAccomMaxPP(e.target.value)}
                      placeholder={t("accommodationMaxPlaceholder")}
                      className={fieldClass()}
                    />
                    <p className="mt-1 text-[11px] leading-snug text-subtle">
                      {t("accommodationMaxHint")}
                    </p>
                  </div>
                  <div>
                    <label htmlFor="accomStars" className={labelClass()}>
                      {t("accommodationStarsLabel")}
                    </label>
                    <select
                      id="accomStars" value={accomMinStars}
                      onChange={(e) => setAccomMinStars(e.target.value)}
                      className={fieldClass()}
                    >
                      <option value="" className="bg-canvas">{t("accommodationStarsAny")}</option>
                      <option value="3" className="bg-canvas">{t("accommodationStars3")}</option>
                      <option value="4" className="bg-canvas">{t("accommodationStars4")}</option>
                      <option value="5" className="bg-canvas">{t("accommodationStars5")}</option>
                    </select>
                    {accomMinStars !== "" && (
                      <p className="mt-1 text-[11px] leading-snug text-warn">
                        {t("accommodationStarsWarning")}
                      </p>
                    )}
                  </div>
                  <div>
                    <label htmlFor="accomRating" className={labelClass()}>
                      {t("accommodationRatingLabel")}
                    </label>
                    <select
                      id="accomRating" value={accomMinRating}
                      onChange={(e) => setAccomMinRating(e.target.value)}
                      className={fieldClass()}
                    >
                      <option value="" className="bg-canvas">{t("accommodationStarsAny")}</option>
                      <option value="4" className="bg-canvas">{t("accommodationRating4")}</option>
                      <option value="4.5" className="bg-canvas">{t("accommodationRating45")}</option>
                    </select>
                    <p className="mt-1 text-[11px] leading-snug text-subtle">
                      {t("accommodationRatingHint")}
                    </p>
                  </div>
                  <div>
                    <label htmlFor="accomLift" className={labelClass()}>
                      {t("accommodationLiftLabel")}
                    </label>
                    <select
                      id="accomLift" value={accomMaxLiftKm}
                      onChange={(e) => setAccomMaxLiftKm(e.target.value)}
                      className={fieldClass()}
                    >
                      <option value="" className="bg-canvas">{t("accommodationStarsAny")}</option>
                      <option value="0.2" className="bg-canvas">{t("accommodationLiftSkiIn")}</option>
                      <option value="0.5" className="bg-canvas">{t("accommodationLiftShortWalk")}</option>
                      <option value="1" className="bg-canvas">{t("accommodationLiftUnder1km")}</option>
                    </select>
                    <p className="mt-1 text-[11px] leading-snug text-subtle">
                      {t("accommodationLiftHint")}
                    </p>
                  </div>
                  <div>
                    <label htmlFor="accomType" className={labelClass()}>
                      {t("accommodationTypeLabel")}
                    </label>
                    <select
                      id="accomType" value={accomPropertyType}
                      onChange={(e) => setAccomPropertyType(e.target.value)}
                      className={fieldClass()}
                    >
                      <option value="HOTELS" className="bg-canvas">{t("accommodationTypeHotels")}</option>
                      <option value="VACATION_RENTALS" className="bg-canvas">
                        {t("accommodationTypeRentals")}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label htmlFor="accomReviews" className={labelClass()}>
                      {t("accommodationReviewsLabel")}
                    </label>
                    <select
                      id="accomReviews" value={accomMinReviews}
                      onChange={(e) => setAccomMinReviews(e.target.value)}
                      className={fieldClass()}
                    >
                      <option value="" className="bg-canvas">{t("accommodationStarsAny")}</option>
                      <option value="50" className="bg-canvas">{t("accommodationReviews50")}</option>
                      <option value="200" className="bg-canvas">{t("accommodationReviews200")}</option>
                    </select>
                    <p className="mt-1 text-[11px] leading-snug text-subtle">
                      {t("accommodationReviewsHint")}
                    </p>
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

                <div>
                  <span className={labelClass()}>{t("skiBagsLabel")}</span>
                  <label className="flex cursor-pointer items-center gap-2 text-sm text-ink">
                    <input
                      type="checkbox"
                      checked={withSkiBags}
                      onChange={(e) => setWithSkiBags(e.target.checked)}
                      className="h-4 w-4 accent-signal"
                    />
                    {t("skiBagsBringing")}
                  </label>
                  <p className="mt-1 text-[11px] text-subtle">{t("skiBagsHint")}</p>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="rounded-lg bg-warn-soft border border-warn/30 px-3 py-2.5 text-sm text-warn">
              {error}
            </div>
          )}

          <CreditMeter credits={credits} pendingCost={pendingCost} />

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
