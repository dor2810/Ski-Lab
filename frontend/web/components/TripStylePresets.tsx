"use client";

import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
import type { RawWeights } from "./PrioritySliders";
import type { AccommodationTier, FoodProfile } from "@/lib/api";

/**
 * One-tap trip styles.
 *
 * WHY THIS EXISTS: the search form asked every visitor to set six
 * abstract priority sliders (ski quality vs. snow reliability vs.
 * convenience...) before it would tell them anything. Someone who
 * skis twice a year, or is just tired, has no idea whether they want
 * "snow reliability 15%" -- and being made to decide is exactly where
 * people give up. Each preset here answers all six at once in the
 * language people actually use about ski trips, and also sets the
 * accommodation and food tiers that go with that intent.
 *
 * The sliders still exist, now behind a "fine-tune" disclosure, so
 * nothing is taken away from the person who does want that control --
 * it just stops being the price of entry.
 *
 * `weights` are RAW relative values, not percentages: PrioritySliders
 * normalizes the set to 100% for display and the API call normalizes
 * again to sum 1.0, so these only need to be right relative to each
 * other.
 */
export type TripStyleId =
  | "balanced"
  | "value"
  | "snow"
  | "easy"
  | "family"
  | "lively"
  | "comfort";

export interface TripStyle {
  id: TripStyleId;
  labelKey: keyof Dictionary;
  blurbKey: keyof Dictionary;
  weights: RawWeights;
  accommodationTier: AccommodationTier;
  foodProfile: FoodProfile;
}

export const TRIP_STYLES: TripStyle[] = [
  {
    id: "balanced",
    labelKey: "styleBalanced",
    blurbKey: "styleBalancedBlurb",
    weights: { ski_quality: 30, price: 20, snow: 15, nightlife: 15, convenience: 10, accommodation: 10, family: 0 },
    accommodationTier: "standard",
    foodProfile: "normal",
  },
  {
    id: "value",
    labelKey: "styleValue",
    blurbKey: "styleValueBlurb",
    weights: { ski_quality: 20, price: 45, snow: 15, nightlife: 5, convenience: 10, accommodation: 5, family: 0 },
    accommodationTier: "budget",
    foodProfile: "budget",
  },
  {
    id: "snow",
    labelKey: "styleSnow",
    blurbKey: "styleSnowBlurb",
    weights: { ski_quality: 30, price: 12, snow: 40, nightlife: 5, convenience: 8, accommodation: 5, family: 0 },
    accommodationTier: "standard",
    foodProfile: "normal",
  },
  {
    id: "easy",
    labelKey: "styleEasy",
    blurbKey: "styleEasyBlurb",
    // Convenience is weighted hardest: a short, simple transfer is what
    // actually makes a trip feel easy for a nervous or tired traveller.
    weights: { ski_quality: 15, price: 15, snow: 10, nightlife: 5, convenience: 35, accommodation: 20, family: 0 },
    accommodationTier: "standard",
    foodProfile: "normal",
  },
  {
    id: "family",
    labelKey: "styleFamily",
    blurbKey: "styleFamilyBlurb",
    // Leans on Resort.family_friendliness, which existed in the data
    // from the start but was never scored until 2026-08-27. Convenience
    // matters nearly as much here: a 3-hour transfer with small children
    // is what actually ruins a family trip.
    weights: { ski_quality: 12, price: 15, snow: 10, nightlife: 0, convenience: 23, accommodation: 15, family: 25 },
    accommodationTier: "standard",
    foodProfile: "normal",
  },
  {
    id: "lively",
    labelKey: "styleLively",
    blurbKey: "styleLivelyBlurb",
    weights: { ski_quality: 25, price: 15, snow: 10, nightlife: 40, convenience: 5, accommodation: 5, family: 0 },
    accommodationTier: "standard",
    foodProfile: "normal",
  },
  {
    id: "comfort",
    labelKey: "styleComfort",
    blurbKey: "styleComfortBlurb",
    weights: { ski_quality: 20, price: 10, snow: 10, nightlife: 5, convenience: 15, accommodation: 40, family: 0 },
    accommodationTier: "luxury",
    foodProfile: "luxury",
  },
];

function StyleIcon({ id }: { id: TripStyleId }) {
  const common = { width: 22, height: 22, viewBox: "0 0 24 24", fill: "none", "aria-hidden": true } as const;
  const stroke = {
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
  };
  switch (id) {
    case "value": // price tag
      return (
        <svg {...common}><path d="M3 12V5a2 2 0 012-2h7l9 9-9 9-9-9z" {...stroke} /><circle cx="7.5" cy="7.5" r="1.4" fill="currentColor" /></svg>
      );
    case "snow": // snowflake
      return (
        <svg {...common}><path d="M12 2v20M4 6l16 12M20 6L4 18" {...stroke} /></svg>
      );
    case "easy": // gentle slope
      return (
        <svg {...common}><path d="M3 18c5 0 8-3 11-7s5-5 7-5" {...stroke} /><circle cx="7" cy="18" r="1.5" fill="currentColor" /></svg>
      );
    case "lively": // music/party
      return (
        <svg {...common}><path d="M9 18V6l10-2v12" {...stroke} /><circle cx="6.5" cy="18" r="2.5" {...stroke} /><circle cx="16.5" cy="16" r="2.5" {...stroke} /></svg>
      );
    case "family": // parent + child
      return (
        <svg {...common}><circle cx="8" cy="6" r="2.5" {...stroke} /><path d="M4 20v-5a4 4 0 018 0v5" {...stroke} /><circle cx="17" cy="11" r="1.8" {...stroke} /><path d="M14 20v-3.5a3 3 0 016 0V20" {...stroke} /></svg>
      );
    case "comfort": // bed
      return (
        <svg {...common}><path d="M3 18v-7h18v7M3 11V7M21 18v-3M3 18h18" {...stroke} /><circle cx="7.5" cy="9" r="1.6" {...stroke} /></svg>
      );
    default: // balanced -- scales
      return (
        <svg {...common}><path d="M12 4v16M6 20h12M4 9h16M7 9l-3 5h6zM17 9l-3 5h6z" {...stroke} /></svg>
      );
  }
}

export function TripStylePresets({
  activeId,
  onPick,
}: {
  activeId: TripStyleId | null;
  onPick: (style: TripStyle) => void;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <p className="mb-1 text-sm font-semibold text-ink">{t("styleQuestion")}</p>
      <p className="mb-3 text-xs text-subtle">{t("styleHint")}</p>

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {TRIP_STYLES.map((style) => {
          const active = style.id === activeId;
          return (
            <button
              type="button"
              key={style.id}
              onClick={() => onPick(style)}
              aria-pressed={active}
              className={`flex flex-col items-start gap-1 rounded-xl border p-3 text-start transition-colors ${
                active
                  ? "border-signal bg-signal-soft"
                  : "border-line bg-surface hover:border-line-strong hover:bg-sunken"
              }`}
            >
              <span className={active ? "text-signal" : "text-sky"}>
                <StyleIcon id={style.id} />
              </span>
              <span className={`text-sm font-semibold ${active ? "text-signal" : "text-ink"}`}>
                {t(style.labelKey)}
              </span>
              <span className="text-[11px] leading-snug text-subtle">{t(style.blurbKey)}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
