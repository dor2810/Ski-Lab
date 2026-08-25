"use client";

import { useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
import { TerrainBar } from "./TerrainBar";
import {
  FlightIcon,
  TransferIcon,
  StayIcon,
  LiftPassIcon,
  GondolaIcon,
  FoodIcon,
  SnowIcon,
  PinIcon,
  ExternalLinkIcon,
} from "./icons";

function LivePill({ live }: { live: boolean }) {
  const { t } = useTranslation();
  return live ? (
    <span
      className="ms-1.5 inline-block rounded-full bg-sky/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-sky align-middle"
      title={t("liveTooltip")}
    >
      {t("liveBadge")}
    </span>
  ) : (
    <span
      className="ms-1.5 inline-block rounded-full bg-ice/10 px-2 py-0.5 text-[10px] font-bold tracking-wide text-ice/60 align-middle"
      title={t("estTooltip")}
    >
      {t("estBadge")}
    </span>
  );
}

const SEASON_KEYS: Record<string, keyof Dictionary> = {
  peak: "seasonPeak",
  high: "seasonHigh",
  shoulder: "seasonShoulder",
};

// Same six dimensions as PrioritySliders' LABEL_KEYS -- the backend's
// score_components dict uses these exact snake_case keys (see
// engine/scoring.score_resort), so the expanded "trip details" panel
// below needs the identical mapping to translate them.
const DIMENSION_KEYS: Record<string, keyof Dictionary> = {
  ski_quality: "priorityShiQuality",
  price: "priorityPrice",
  snow: "prioritySnow",
  nightlife: "priorityNightlife",
  convenience: "priorityConvenience",
  accommodation: "priorityAccommodation",
};

// Deep links to Google's own live search results, NOT a booking link
// for this exact priced itinerary -- see api/engine/links.py's module
// docstring on the backend for why (resolving the provider's opaque
// booking_token into a real bookable page needs a live API call per
// result, which this project's rate-limited quota can't spend on every
// card in every search). searchLinkDisclaimer makes that explicit
// rather than letting the link imply more precision than it has.
function SearchLinkButton({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-full border border-white/15 px-3 py-1.5 text-xs font-semibold text-sky hover:border-sky/60 hover:bg-sky/10"
    >
      <ExternalLinkIcon size={13} />
      {label}
    </a>
  );
}

function lineItems(r: TripResult): { icon: typeof FlightIcon; labelKey: keyof Dictionary; value: number; live: boolean | null }[] {
  return [
    { icon: FlightIcon, labelKey: "lineFlight", value: r.cost.flight_eur, live: r.cost.flight_price_is_live },
    { icon: TransferIcon, labelKey: "lineTransfer", value: r.cost.transfer_eur, live: null },
    {
      icon: StayIcon,
      labelKey: "lineAccommodation",
      value: r.cost.accommodation_eur,
      live: r.cost.accommodation_price_is_live,
    },
    { icon: LiftPassIcon, labelKey: "lineLiftPass", value: r.cost.ski_pass_eur, live: null },
    { icon: GondolaIcon, labelKey: "lineEquipment", value: r.cost.equipment_eur, live: null },
    { icon: FoodIcon, labelKey: "lineFood", value: r.cost.food_eur, live: null },
  ];
}

export function ResultCard({ result }: { result: TripResult }) {
  const { t, locale } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const r = result;
  const scorePct = Math.round(r.score * 100);

  return (
    <article
      className={`animate-rise-in rounded-2xl border p-6 sm:p-7 ${
        r.within_budget
          ? "border-white/10 bg-midnight"
          : "border-amber-400/40 bg-midnight ring-1 ring-amber-400/20"
      }`}
    >
      {!r.within_budget && (
        <div className="mb-4 rounded-lg bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-300">
          {t("overBudgetBanner")}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {/* Resort/country names are proper nouns from the backend --
              deliberately not translated, see ResortPicker's comment. */}
          <h3 className="text-xl font-bold text-white">{r.resort.name}</h3>
          <p className="text-sm text-ice/60">{r.resort.country}</p>
          {r.start_date && r.end_date && (
            <p className="mt-1 text-sm text-sky">
              {formatDate(r.start_date, locale)} – {formatDate(r.end_date, locale)}
              {r.season && SEASON_KEYS[r.season] && (
                <span className="ms-2 rounded bg-white/5 px-1.5 py-0.5 text-[11px] font-semibold text-ice/70">
                  {t(SEASON_KEYS[r.season])}
                </span>
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="text-end">
            <div className="text-3xl font-extrabold tabular-nums text-white">
              {formatEUR(r.cost.total_eur, locale)}
            </div>
            <div className="text-xs text-ice/50">{t("perPersonTotal")}</div>
          </div>
          <div
            className="flex h-12 w-12 flex-none items-center justify-center rounded-full border-2 border-sky/60 text-sm font-bold text-sky"
            title={t("matchScoreTitle")}
          >
            {scorePct}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        {lineItems(r).map(({ icon: Icon, labelKey, value, live }) => (
          <div key={labelKey} className="flex items-center gap-2 text-sm">
            <Icon size={16} className="flex-none text-sky" />
            <span className="text-ice/70">{t(labelKey)}</span>
            <span className="ms-auto font-semibold tabular-nums text-white">
              {formatEUR(value, locale)}
            </span>
            {live !== null && <LivePill live={live} />}
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        {r.flight_search_url && (
          <SearchLinkButton href={r.flight_search_url} label={t("viewFlights")} />
        )}
        <SearchLinkButton href={r.accommodation_search_url} label={t("viewAccommodation")} />
        <span className="text-[11px] text-ice/40">{t("searchLinkDisclaimer")}</span>
      </div>

      <div className="mt-6">
        <TerrainBar terrain={r.resort.terrain} />
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ice/60">
        <span>{t("kmPiste", { km: r.resort.piste_km })}</span>
        <span className="flex items-center gap-1">
          <PinIcon size={12} /> {t("minFromAirport", { min: Math.round(r.resort.transfer_time_minutes), airport: r.resort.nearest_airport })}
        </span>
        <span>{t("offPisteRating", { n: r.resort.off_piste_rating })}</span>
        <span className="flex items-center gap-1">
          <SnowIcon size={12} /> {t("snowRating", { n: r.resort.snow_reliability })}
        </span>
        <span>{t("nightlifeRating", { n: r.resort.nightlife_rating })}</span>
      </div>

      {/* r.explanation comes pre-translated from the backend (see
          nlp/explainer.py's lang param) and already starts with the
          localized "Why:" equivalent -- no separate label needed here. */}
      <p className="mt-4 text-sm leading-relaxed text-ice/80">{r.explanation}</p>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="mt-5 text-sm font-semibold text-sky hover:text-sky/80"
      >
        {expanded ? t("hideTripDetails") : t("viewTripDetails")}
      </button>

      {expanded && (
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 border-t border-white/10 pt-4 text-xs sm:grid-cols-3">
          {Object.entries(r.score_components).map(([dim, val]) => (
            <div key={dim} className="flex justify-between text-ice/60">
              <span className="capitalize">{DIMENSION_KEYS[dim] ? t(DIMENSION_KEYS[dim]) : dim.replace("_", " ")}</span>
              <span className="tabular-nums text-ice/80">{Math.round(val * 100)}%</span>
            </div>
          ))}
          {r.resort.needs_verification && (
            <p className="col-span-full mt-1 text-amber-300/80">{t("needsVerificationNote")}</p>
          )}
        </div>
      )}
    </article>
  );
}
