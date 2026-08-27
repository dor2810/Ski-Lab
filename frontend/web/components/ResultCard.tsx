"use client";

import { useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
import { TerrainBar } from "./TerrainBar";
import { WeatherWeek } from "./WeatherWeek";
import { WhatsIncluded } from "./WhatsIncluded";
import { FlightOptions } from "./FlightOptions";
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

// Three honest states, not two. "LIVE" = quoted per-request just now;
// "REAL" = a genuinely published price we researched (lift passes,
// transfers), which is sourced but not per-request; "EST." = the seed
// spreadsheet's estimate. Collapsing the middle case into either
// neighbour would misrepresent it in one direction or the other.
function SourcePill({ kind }: { kind: "live" | "researched" | "estimated" }) {
  const { t } = useTranslation();
  if (kind === "researched") {
    return (
      <span
        className="ms-1.5 inline-block rounded-full bg-signal-soft px-2 py-0.5 text-[10px] font-bold tracking-wide text-signal align-middle"
        title={t("researchedTooltip")}
      >
        {t("researchedBadge")}
      </span>
    );
  }
  const live = kind === "live";
  return live ? (
    <span
      className="ms-1.5 inline-block rounded-full bg-sky/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-sky align-middle"
      title={t("liveTooltip")}
    >
      {t("liveBadge")}
    </span>
  ) : (
    <span
      className="ms-1.5 inline-block rounded-full bg-sunken px-2 py-0.5 text-[10px] font-bold tracking-wide text-subtle align-middle"
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
  family: "priorityFamily",
};

// Deep links to Google's own live results. For the single top-ranked
// card, flight/accommodation links usually land directly on the
// specific priced flight/hotel -- resolving that needs a live lookup
// per card, which this project's rate-limited quota can only spend on
// the one result actually being shown as the best match, not on every
// card in a list (see api/routes/search.py's _flight_search_url/
// _accommodation_search_url on the backend for the exact contract and
// fallback). Every other card, and any case where that live match
// failed, gets Google's plain search results instead --
// searchLinkDisclaimer says as much rather than implying every link
// is equally precise.
function SearchLinkButton({ href, label }: { href: string; label: string }) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 rounded-full border border-line px-3 py-1.5 text-xs font-semibold text-sky hover:border-sky/60 hover:bg-sky/10"
    >
      <ExternalLinkIcon size={13} />
      {label}
    </a>
  );
}

type SourceKind = "live" | "researched" | "estimated" | null;

function lineItems(r: TripResult): { icon: typeof FlightIcon; labelKey: keyof Dictionary; value: number; source: SourceKind }[] {
  return [
    { icon: FlightIcon, labelKey: "lineFlight", value: r.cost.flight_eur,
      source: r.cost.flight_price_is_live ? "live" : "estimated" },
    { icon: TransferIcon, labelKey: "lineTransfer", value: r.cost.transfer_eur, source: null },
    {
      icon: StayIcon,
      labelKey: "lineAccommodation",
      value: r.cost.accommodation_eur,
      source: r.cost.accommodation_price_is_live ? "live" : "estimated",
    },
    { icon: LiftPassIcon, labelKey: "lineLiftPass", value: r.cost.ski_pass_eur,
      source: r.cost.ski_pass_price_is_researched ? "researched" : "estimated" },
    { icon: GondolaIcon, labelKey: "lineEquipment", value: r.cost.equipment_eur, source: null },
    { icon: FoodIcon, labelKey: "lineFood", value: r.cost.food_eur, source: null },
  ];
}

export function ResultCard({ result }: { result: TripResult }) {
  const { t, locale } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const r = result;
  const scorePct = Math.round(r.score * 100);

  return (
    <article
      className={`animate-rise-in rounded-2xl border p-4 sm:p-7 ${
        r.within_budget
          ? "border-line bg-surface"
          : "border-warn/40 bg-surface ring-1 ring-warn/20"
      }`}
    >
      {!r.within_budget && (
        <div className="mb-4 rounded-lg bg-warn-soft px-3 py-2 text-xs font-semibold text-warn">
          {t("overBudgetBanner")}
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {/* Resort/country names are proper nouns from the backend --
              deliberately not translated, see ResortPicker's comment. */}
          <h3 className="text-xl font-bold text-ink">{r.resort.name}</h3>
          <p className="text-sm text-subtle">{r.resort.country}</p>
          {r.start_date && r.end_date && (
            <p className="mt-1 text-sm text-sky">
              {formatDate(r.start_date, locale)} – {formatDate(r.end_date, locale)}
              {r.season && SEASON_KEYS[r.season] && (
                <span className="ms-2 rounded bg-sunken px-1.5 py-0.5 text-[11px] font-semibold text-muted">
                  {t(SEASON_KEYS[r.season])}
                </span>
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="text-end">
            <div className="text-3xl font-extrabold tabular-nums text-ink">
              {formatEUR(r.cost.total_eur, locale)}
            </div>
            <div className="text-xs text-subtle">{t("perPersonTotal")}</div>
          </div>
          <div
            className="flex h-12 w-12 flex-none items-center justify-center rounded-full border-2 border-sky/60 text-sm font-bold text-sky"
            title={t("matchScoreTitle")}
          >
            {scorePct}
          </div>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-1 gap-x-6 gap-y-2 sm:grid-cols-2 sm:gap-y-2.5 lg:grid-cols-3">
        {lineItems(r).map(({ icon: Icon, labelKey, value, source }) => (
          <div key={labelKey} className="flex min-w-0 items-center gap-2 text-sm">
            <Icon size={16} className="flex-none text-sky" />
            <span className="truncate text-muted">{t(labelKey)}</span>
            <span className="ms-auto whitespace-nowrap font-semibold tabular-nums text-ink">
              {formatEUR(value, locale)}
            </span>
            {source !== null && <SourcePill kind={source} />}
          </div>
        ))}
      </div>

      {r.accommodation_property_name && (
        <p className="mt-4 text-sm text-muted">
          <StayIcon size={14} className="me-1.5 inline-block align-text-bottom text-sky" />
          {t("accommodationPropertyNamePrefix")} <span className="font-semibold text-ink">{r.accommodation_property_name}</span>
        </p>
      )}

      <div className={`flex flex-wrap items-center gap-2 ${r.accommodation_property_name ? "mt-2" : "mt-4"}`}>
        {r.flight_search_url && (
          <SearchLinkButton href={r.flight_search_url} label={t("viewFlights")} />
        )}
        <SearchLinkButton href={r.accommodation_search_url} label={t("viewAccommodation")} />
        <SearchLinkButton href={r.transfer_search_url} label={t("viewTransfer")} />
        <SearchLinkButton href={r.equipment_search_url} label={t("viewEquipment")} />
        <SearchLinkButton href={r.ski_pass_search_url} label={t("viewSkiPass")} />
        <span className="text-[11px] text-subtle">{t("searchLinkDisclaimer")}</span>
      </div>

      <FlightOptions options={r.flight_options} />

      <WhatsIncluded />

      <WeatherWeek weather={r.weather} />

      <div className="mt-5">
        <TerrainBar terrain={r.resort.terrain} />
      </div>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-subtle">
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
      <p className="mt-3 text-sm leading-relaxed text-muted">{r.explanation}</p>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="mt-4 text-sm font-semibold text-sky hover:text-sky/80"
      >
        {expanded ? t("hideTripDetails") : t("viewTripDetails")}
      </button>

      {expanded && (
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 border-t border-line pt-4 text-xs sm:grid-cols-3">
          {Object.entries(r.score_components).map(([dim, val]) => (
            <div key={dim} className="flex justify-between text-subtle">
              <span className="capitalize">{DIMENSION_KEYS[dim] ? t(DIMENSION_KEYS[dim]) : dim.replace("_", " ")}</span>
              <span className="tabular-nums text-muted">{Math.round(val * 100)}%</span>
            </div>
          ))}
          {r.resort.needs_verification && (
            <p className="col-span-full mt-1 text-warn">{t("needsVerificationNote")}</p>
          )}
        </div>
      )}
    </article>
  );
}
