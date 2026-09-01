"use client";

import { useEffect, useRef, useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate, formatShortDate } from "@/lib/format";
import { tripTotalWith } from "@/lib/tripTotal";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";
import { TerrainBar } from "./TerrainBar";
import { WeatherWeek } from "./WeatherWeek";
import { WhatsIncluded } from "./WhatsIncluded";
import { FlightOptions } from "./FlightOptions";
import { TransferOptions } from "./TransferOptions";
import { JourneyTimeline } from "./JourneyTimeline";
import { CostInstrument, type FlashTarget } from "./CostInstrument";
import { TripDetails, HandoffLink, type TabKey } from "./TripDetails";
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

/** How long a handoff link stays called out, in ms. */
const FLASH_MS = 2600;

export function ResultCard({ result, variants, maxConnections = null, focus = null }: {
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
  /**
   * "Show me this resort on this date" -- sent by the price views when
   * a day is clicked. Carries a seq so that clicking the SAME day
   * twice still scrolls; a bare date would be an unchanged prop.
   */
  focus?: { date: string; seq: number } | null;
}) {
  const { t, locale } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const deals = variants && variants.length > 0 ? variants : [result];
  const [dealIdx, setDealIdx] = useState(0);
  // Which flight/transfer the journey timeline describes. Reset
  // when the deal changes -- option lists differ per date.
  const [transferIdx, setTransferIdx] = useState(0);
  const [flightIdx, setFlightIdx] = useState(0);
  const [stayIdx, setStayIdx] = useState(0);
  // Details visibility lives HERE so the cost breakdown can open it to
  // a specific tab -- clicking "Flight" should land you on the flight
  // list, not merely reveal a closed accordion.
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [detailsTab, setDetailsTab] = useState<TabKey>("getting");

  // A handoff link called out for a moment after the traveller lands
  // on its tab -- see HandoffLink's `flash`.
  const cardRef = useRef<HTMLElement>(null);
  // Bumped on every breakdown -> detail jump, so a repeat click on
  // the same line scrolls again.
  const [navSeq, setNavSeq] = useState(0);
  const [flash, setFlash] = useState<FlashTarget | null>(null);

  // Long enough to notice and follow, short enough not to become
  // permanent decoration on a link you have already seen.
  // Every jump from the cost breakdown brings the CARD's bottom edge to
  // the bottom of the screen. Not the clicked line, and not the target
  // link: centring either threw the page past what was being read.
  // Keyed on a counter so clicking the same line twice still scrolls.
  useEffect(() => {
    if (navSeq === 0) return;
    const card = cardRef.current;
    if (!card) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Two frames: the tab has to open and lay out before the card has
    // its final height.
    const id = requestAnimationFrame(() => requestAnimationFrame(() => {
      card.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "end" });
    }));
    return () => cancelAnimationFrame(id);
  }, [navSeq]);

  useEffect(() => {
    if (!flash) return;
    const id = window.setTimeout(() => setFlash(null), FLASH_MS);
    return () => window.clearTimeout(id);
  }, [flash]);

  function showDetail(tab: TabKey, target?: FlashTarget) {
    setDetailsTab(tab);
    setDetailsOpen(true);
    setFlash(target ?? null);
    setNavSeq((n) => n + 1);
  }

  const r = deals[Math.min(dealIdx, deals.length - 1)];

  // Arriving from a price view: switch to that date, then bring the
  // card to the top of the screen and mark it, so it is obvious which
  // of several cards just answered.
  const [arrived, setArrived] = useState(false);
  useEffect(() => {
    if (!focus) return;
    const i = deals.findIndex((d) => d.start_date === focus.date);
    if (i >= 0) {
      setDealIdx(i);
      setTransferIdx(0);
      setFlightIdx(0);
      setStayIdx(0);
    }
    const card = cardRef.current;
    if (card) {
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
      requestAnimationFrame(() => {
        card.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
      });
    }
    setArrived(true);
    const id = window.setTimeout(() => setArrived(false), FLASH_MS);
    return () => window.clearTimeout(id);
    // deals is derived from props and stable for a given result set.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus]);

  // The traveller's current choices, so every "whole trip" figure on
  // the card is quoted against the same trip.
  const chosenFlightEur = r.flight_options?.[flightIdx]?.price_eur ?? r.cost.flight_eur;
  const chosenTransferEur =
    r.transfer_options?.[transferIdx]?.price_eur_per_person ?? r.cost.transfer_eur;
  const chosenStayEur = r.accommodation_options?.[stayIdx]?.per_person_eur ?? r.cost.accommodation_eur;

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
      ref={cardRef}
      // scroll-mt clears the 64px fixed header: without it, jumping to a
      // card from the price views parked the resort name behind the bar.
      className={`animate-rise-in scroll-mt-20 rounded-2xl border p-4 sm:p-7 transition-shadow duration-500 ${
        r.within_budget
          ? "border-line bg-surface"
          : "border-warn/40 bg-surface ring-1 ring-warn/20"
      } ${arrived ? "ring-2 ring-signal" : ""}`}
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
          {/* The price used to live here, competing with the cost
              instrument's own total further down the card. One total
              per card: the instrument owns it, because there the sum
              sits with the parts it is made of. */}
          <div
            className="flex h-14 w-14 flex-none flex-col items-center justify-center rounded-full border-2 border-sky/60 leading-none text-sky"
            title={t("matchScoreTitle")}
          >
            <span className="text-sm font-bold">{scorePct}</span>
            <span className="mt-0.5 text-[9px] uppercase tracking-wide opacity-80">
              {t("matchScoreLabel")}
            </span>
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
                onClick={() => { setDealIdx(i); setTransferIdx(0); setFlightIdx(0); setStayIdx(0); }}
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

      <JourneyTimeline result={r} transferIndex={transferIdx} flightIndex={flightIdx}   onNavigate={showDetail}
      />

      <CostInstrument
        result={r}
        flightIndex={flightIdx}
        transferIndex={transferIdx}
        stayIndex={stayIdx}
        onNavigate={showDetail}
      />

      {/* EVIDENCE, behind one disclosure. Everything below used to be
          eight peer blocks making the card 2,662px tall at 1280px --
          which buried the cost instrument and made comparing trips
          impossible. Each partner hand-off now lives inside the
          section it belongs to instead of a five-button cluster. */}
      <TripDetails
        result={r}
        open={detailsOpen}
        onOpenChange={setDetailsOpen}
        tab={detailsTab}
        onTabChange={setDetailsTab}
        gettingThere={
          <>
            <FlightOptions
              options={r.flight_options}
              booking={booking}
              selectedIndex={flightIdx}
              onSelect={setFlightIdx}
              tripTotalFor={(flightEur) => tripTotalWith(r.cost, {
                flightEur, transferEur: chosenTransferEur, stayEur: chosenStayEur })}
              defaultOpen
            />
            <TransferOptions
              options={r.transfer_options ?? []}
              selectedIndex={transferIdx}
              onSelect={setTransferIdx}
              defaultOpen
            />
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
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <HandoffLink href={r.flight_search_url} label={t("viewFlights")} />
              <HandoffLink href={r.transfer_search_url} label={t("viewTransfer")} />
            </div>
            <MoreDates resortName={r.resort.name} alternatives={r.alternative_dates} />
          </>
        }
        staying={
          <>
            {r.accommodation_property_name && (
              <p className="text-sm text-muted">
                <StayIcon size={14} className="me-1.5 inline-block align-text-bottom text-sky" />
                {t("accommodationPropertyNamePrefix")}{" "}
                <span className="font-semibold text-ink">{r.accommodation_property_name}</span>
              </p>
            )}
            {/* When a filter prices every real property out, the trip
                falls back to a static ESTIMATE that may itself exceed
                the budget that was set. Saying so is the difference
                between an answer and a silent shrug. */}
            {r.accommodation_choice?.priced_on_an_estimate && (
              <p className="mt-2 rounded-lg border border-warn/40 bg-warn-soft px-3 py-2 text-[11px] leading-snug text-warn">
                {r.accommodation_choice.cheapest_available_eur_per_person != null
                  ? t("accommodationNoneFitCheapest", {
                      resort: r.resort.name,
                      price: formatEUR(r.accommodation_choice.cheapest_available_eur_per_person, locale),
                    })
                  : t("accommodationNoneFit", { resort: r.resort.name })}
              </p>
            )}
            {r.accommodation_choice
              && !r.accommodation_choice.priced_on_an_estimate
              && r.accommodation_choice.matched === 0
              && r.accommodation_choice.provider_vetted > 0 && (
              <p className="mt-2 text-[11px] leading-snug text-subtle">
                {t("accommodationVettedNote", {
                  n: String(r.accommodation_choice.provider_vetted),
                })}
              </p>
            )}
            {r.accommodation_choice?.fell_back_to_unrated && (
              <p className="mt-2 text-[11px] leading-snug text-warn">
                {t("accommodationFellBackUnrated", { resort: r.resort.name })}
              </p>
            )}
            {r.accommodation_choice?.fell_back_below_floor && (
              <p className="mt-2 text-[11px] leading-snug text-warn">
                {t("accommodationFellBackBelow", { resort: r.resort.name })}
              </p>
            )}
            <AccommodationOptions
              options={r.accommodation_options}
              selectedIndex={stayIdx}
              onSelect={setStayIdx}
              tripTotalFor={(stayEur) => tripTotalWith(r.cost, {
                flightEur: chosenFlightEur, transferEur: chosenTransferEur, stayEur })}
              defaultOpen
            />
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <HandoffLink href={r.accommodation_search_url} label={t("viewAccommodation")} />
              <HandoffLink href={r.ski_pass_search_url} label={t("viewSkiPass")}
                           flash={flash === "skiPass"} />
              <HandoffLink href={r.equipment_search_url} label={t("viewEquipment")}
                           flash={flash === "equipment"} />
            </div>
            <WhatsIncluded />
            <p className="mt-2 text-[11px] text-subtle">{t("searchLinkDisclaimer")}</p>
          </>
        }
        conditions={
          <>
            <WeatherWeek weather={r.weather} />
            <div className="mt-4">
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
          </>
        }
      />
    </article>
  );
}
