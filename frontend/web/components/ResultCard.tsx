"use client";

import { useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate, formatShortDate } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
import { TerrainBar } from "./TerrainBar";
import { WeatherWeek } from "./WeatherWeek";
import { WhatsIncluded } from "./WhatsIncluded";
import { FlightOptions } from "./FlightOptions";
import { TransferOptions } from "./TransferOptions";
import { JourneyTimeline } from "./JourneyTimeline";
import { AccommodationOptions } from "./AccommodationOptions";
import { MoreDates } from "./MoreDates";
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
    { icon: TransferIcon, labelKey: "lineTransfer", value: r.cost.transfer_eur,
      // LIVE only when this exact date/party/pickup-time was quoted by
      // the operator just now; the curated rate-card figure stays
      // unbadged rather than borrowing a label it hasn't earned.
      source: r.cost.transfer_price_is_live ? "live" : null },
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

function formatMinutes(minutes: number | null): string {
  if (minutes == null) return "";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  return h ? `${h}h${String(m).padStart(2, "0")}` : `${m}min`;
}

export function ResultCard({ result, variants, maxConnections = null }: {
  result: TripResult;
  // Every result the search returned FOR THIS RESORT, rank order --
  // the owner's ask: "Val Thorens and the best deal it found and some
  // button to switch to the second best deal... without needing a
  // long list." One card per resort; the pager flips between its
  // full results (each with its own dates, costs, flights, hotels --
  // they are complete results, not lightweight previews).
  variants?: TripResult[];
  // The max-connections preference the search ran with -- needed by
  // the per-flight booking link, which re-runs the same query at
  // click time (see FlightOptions' BookingContext). Absent for the
  // landing-page preview, which has no flight options anyway.
  maxConnections?: number | null;
}) {
  const { t, locale } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const deals = variants && variants.length > 0 ? variants : [result];
  const [dealIdx, setDealIdx] = useState(0);
  const r = deals[Math.min(dealIdx, deals.length - 1)];
  // Dated results (the real search path) carry their own trip dates;
  // without them the booking endpoint has nothing to re-search.
  const booking = r.start_date && r.end_date
    ? {
        resortName: r.resort.name,
        outboundDate: r.start_date,
        returnDate: r.end_date,
        maxConnections,
        flightSearchUrl: r.flight_search_url,
      }
    : null;
  const scorePct = Math.round(r.score * 100);
  // Only a range when the two ends genuinely differ -- a range like
  // "EUR1322-EUR1322" is noise, and rounding can make a trivial
  // difference look like one.
  const showRange =
    r.total_eur_with_fastest_flight != null &&
    Math.round(r.total_eur_with_fastest_flight) > Math.round(r.cost.total_eur);

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
            {/* A RANGE, not a single number, whenever the flight choice
                genuinely moves the total. Showing only the low end
                quietly assumes the traveller takes the cheapest
                itinerary, which on real searches has meant a 24-hour
                journey. The low end stays visually dominant because it
                IS what the ranking used. */}
            <div className="text-2xl font-extrabold tabular-nums leading-tight text-ink sm:text-3xl">
              {formatEUR(r.cost.total_eur, locale)}
              {showRange && (
                <span className="block text-base font-bold text-muted sm:inline sm:text-lg">
                  <span className="hidden sm:inline">{"\u2013"}</span>
                  <span className="sm:hidden">{"\u2013 "}</span>
                  {formatEUR(r.total_eur_with_fastest_flight as number, locale)}
                </span>
              )}
            </div>
            <div className="mt-1 text-xs text-subtle">
              {showRange ? t("perPersonTotalRange") : t("perPersonTotal")}
            </div>
          </div>
          <div
            className="flex h-12 w-12 flex-none items-center justify-center rounded-full border-2 border-sky/60 text-sm font-bold text-sky"
            title={t("matchScoreTitle")}
          >
            {scorePct}
          </div>
        </div>
      </div>

      {/* PRICE-BY-START-DATE switcher (replaces the ‹ › arrows, owner's
          ask): one chip per deal, chronological, each carrying its date
          AND its total so the whole price-by-date picture is visible at
          a glance -- pressing a chip swaps the entire card to that
          deal, exactly as the arrows did. The engine's best deal is
          the pre-selected one (deals[0]); chips are merely sorted by
          date for scanning, so "first chip" ≠ "best" on purpose.
          Over-budget deals show their price in the warn tone. */}
      {deals.length > 1 && (
        <div
          role="group"
          aria-label={t("dealByDateLabel")}
          className="mt-3 flex flex-wrap gap-1.5"
        >
          {deals
            .map((d, i) => ({ d, i }))
            .sort((a, b) =>
              a.d.start_date && b.d.start_date
                ? a.d.start_date.localeCompare(b.d.start_date)
                : a.i - b.i
            )
            .map(({ d, i }) => (
              <button
                key={i}
                type="button"
                aria-pressed={i === dealIdx}
                onClick={() => setDealIdx(i)}
                className={`flex items-baseline gap-1.5 rounded-lg border px-2.5 py-1 text-xs transition-colors ${
                  i === dealIdx
                    ? "border-signal bg-signal font-semibold text-white"
                    : "border-line bg-sunken text-muted hover:border-line-strong"
                }`}
              >
                <span>{d.start_date ? formatShortDate(d.start_date, locale) : t("dealOf", { i: String(i + 1), n: String(deals.length) })}</span>
                <span
                  className={`font-bold tabular-nums ${
                    i === dealIdx ? "" : d.within_budget ? "text-ink" : "text-warn"
                  }`}
                >
                  {formatEUR(d.cost.total_eur, locale)}
                </span>
              </button>
            ))}
        </div>
      )}

      <JourneyTimeline result={r} />

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

      {/* Transfer provenance -- a real Alps2Alps price, or the real
          drive figures with (in the tooltip) the exact reason there is
          no operator quote. Never a silent estimate. */}
      {r.transfer_info && (
        <p className="mt-2 text-[11px] leading-snug text-subtle"
           title={r.transfer_info.unavailable_reason ?? undefined}>
          {r.transfer_info.source === "alps2alps_live" && r.transfer_info.price_eur != null
            ? t("transferLiveQuote", {
                price: String(Math.round(r.transfer_info.price_eur)),
                vehicle: r.transfer_info.vehicle_name ?? "",
                pickup: r.transfer_info.pickup_time ?? "",
              })
            : r.transfer_info.source === "alps2alps" && r.transfer_info.price_eur != null
            ? t("transferRealQuote", {
                price: String(Math.round(r.transfer_info.price_eur)),
                dur: formatMinutes(r.transfer_info.duration_minutes),
              })
            : r.transfer_info.duration_minutes != null
              ? t("transferDriveOnly", {
                  iata_free: "",
                  dur: formatMinutes(r.transfer_info.duration_minutes),
                  km: String(Math.round(r.transfer_info.distance_km ?? 0)),
                })
              : null}
        </p>
      )}

      {/* TIME-ALIGNMENT WARNING (owner's ask): the transfer is quoted
          around this itinerary's own landing time, and the return
          pickup is the operator's own calculation from the return
          flight's departure -- but the traveller may book a different
          flight than the one shown, so the times must be re-checked at
          booking. Shown whenever a live quote exists, with the actual
          times in it rather than a vague "check your times". */}
      {r.transfer_info?.source === "alps2alps_live" && (
        <p className="mt-2 rounded-lg border border-warn/30 bg-warn-soft px-3 py-2 text-[11px] leading-snug text-warn">
          {t("transferTimeAlignmentNote", { pickup: r.transfer_info.pickup_time ?? "" })}
          {/* The homeward clause only when the operator actually gave
              us a return pickup -- it needs the RETURN FLIGHT's
              departure time, which only some providers expose. An
              empty slot in the sentence would read as a broken string
              (caught in live review). */}
          {r.transfer_info.return_pickup_time
            && ` ${t("transferReturnPickupNote", { ret: r.transfer_info.return_pickup_time })}`}
          {r.transfer_info.is_private && ` ${t("transferPrivateNote")}`}
        </p>
      )}

      <MoreDates resortName={r.resort.name} alternatives={r.alternative_dates} />

      <FlightOptions options={r.flight_options} booking={booking} />

      <TransferOptions options={r.transfer_options ?? []} />

      <AccommodationOptions options={r.accommodation_options} />

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
