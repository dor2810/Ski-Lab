"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import { useAuth } from "@/lib/auth/context";
import { fetchFlightBookingLink, type FlightOption } from "@/lib/api";
import { FlightIcon } from "./icons";

/**
 * The real itineraries behind a result's flight price -- the curated
 * Cheapest / Best / Fastest picks (engine/flight_picks.py), each with
 * its flight numbers, whole-trip total, and a "book" action that
 * fetches a Google Flights booking-page deep link for exactly that
 * itinerary at click time.
 *
 * WHY THIS EXISTS: the flight search always returned a LIST of priced
 * flights and we kept one number off it. On a real TLV->GVA search the
 * cheapest was EUR283 for a FOURTEEN AND A HALF HOUR journey, while
 * EUR392 got there in six hours and a nonstop was 3h35. Showing only
 * the EUR283 makes the trip total look great while silently assuming
 * the traveller will spend two full days getting there.
 *
 * The labels are the triad travellers already know -- Skyscanner's
 * default sort is literally called "Best" (price vs. convenience),
 * alongside Cheapest and Fastest. Not "Luxury": we have no cabin-class
 * data, so that word would claim knowledge of the seat we don't have.
 */

// How much longer than the fastest option a flight has to be before it
// is worth warning about. Judgement, not a sourced figure: four hours
// is roughly the point where a stopover stops being an inconvenience
// and costs you a day of the trip.
const PUNISHING_EXTRA_MINUTES = 4 * 60;

function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m === 0 ? `${h}h` : `${h}h${String(m).padStart(2, "0")}`;
}

/** Props the booking-link endpoint needs to re-find this itinerary. */
export interface BookingContext {
  resortName: string;
  outboundDate: string; // YYYY-MM-DD
  returnDate: string; // YYYY-MM-DD
  maxConnections: number | null;
  /** The always-working fallback when a deep link can't be built. */
  flightSearchUrl: string | null;
}

function RoleBadge({ role }: { role: string }) {
  const { t } = useTranslation();
  const label =
    role === "cheapest" ? t("flightRoleCheapest")
    : role === "best" ? t("flightRoleBest")
    : role === "fastest" ? t("flightRoleFastest")
    : null;
  if (!label) return null;
  // "best" carries the accent -- it is the recommendation; the other
  // two are factual extremes and stay quiet.
  const tone = role === "best"
    ? "bg-signal text-white"
    : "bg-sunken text-muted border border-line";
  return (
    <span className={`rounded-full px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide ${tone}`}>
      {label}
    </span>
  );
}

function BookFlightButton({ option, booking }: { option: FlightOption; booking: BookingContext }) {
  const { t } = useTranslation();
  const { runAuthed } = useAuth();
  const [busy, setBusy] = useState(false);

  // A Kiwi-sourced option ships its booking deep link right in the
  // search response -- no click-time fetch, just a plain link.
  if (option.booking_url) {
    return (
      <a
        href={option.booking_url}
        target="_blank"
        rel="noopener noreferrer"
        className="flex-none rounded-md bg-signal-soft px-2 py-0.5 text-[11px] font-semibold text-signal hover:bg-signal hover:text-white"
      >
        {t("flightBook")}
      </a>
    );
  }

  // Only offered when the itinerary is identifiable: without flight
  // numbers the endpoint has nothing stable to match, and the row's
  // generic search link already exists one level up on the card.
  if (option.flight_numbers.length === 0) return null;

  async function onClick() {
    // Open the window synchronously so the popup blocker treats it as
    // user-initiated, then point it at the link once fetched.
    const popup = window.open("about:blank", "_blank");
    setBusy(true);
    try {
      const { url } = await runAuthed((token) =>
        fetchFlightBookingLink(
          {
            resort_name: booking.resortName,
            outbound_date: booking.outboundDate,
            return_date: booking.returnDate,
            flight_numbers: option.flight_numbers,
            max_connections: booking.maxConnections,
          },
          token
        )
      );
      const target = url ?? booking.flightSearchUrl;
      if (popup && target) popup.location.href = target;
      else if (popup) popup.close();
    } catch {
      // Degrade to the plain dated search link -- never a dead popup.
      if (popup && booking.flightSearchUrl) popup.location.href = booking.flightSearchUrl;
      else if (popup) popup.close();
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      className="flex-none rounded-md bg-signal-soft px-2 py-0.5 text-[11px] font-semibold text-signal hover:bg-signal hover:text-white disabled:opacity-60"
    >
      {busy ? t("flightBookLoading") : t("flightBook")}
    </button>
  );
}

export function FlightOptions({ options, booking }: { options: FlightOption[]; booking: BookingContext | null }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!options || options.length === 0) return null;

  const cheapest = options[0];
  const fastest = options.reduce((a, b) => (a.duration_minutes <= b.duration_minutes ? a : b));
  // Only worth flagging when a real, better-value alternative exists:
  // the cheapest is genuinely punishing AND something faster is here.
  const cheapestIsPunishing =
    cheapest.duration_minutes - fastest.duration_minutes >= PUNISHING_EXTRA_MINUTES;

  return (
    <div className="mt-2 rounded-lg border border-line bg-surface px-3 py-2.5">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-ink hover:text-signal"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <FlightIcon size={14} className="flex-none" />
          <span className="truncate">{t("flightOptionsTitle", { count: String(options.length) })}</span>
        </span>
        <span aria-hidden="true" className="text-base leading-none text-subtle">{open ? "\u2212" : "+"}</span>
      </button>

      {cheapestIsPunishing && (
        <p className="mt-1.5 text-[11px] leading-snug text-warn">
          {t("flightCheapestIsSlow", {
            cheapDuration: formatDuration(cheapest.duration_minutes),
            fastDuration: formatDuration(fastest.duration_minutes),
            extra: String(Math.round(fastest.price_eur - cheapest.price_eur)),
          })}
        </p>
      )}

      {open && (
        <ul className="mt-2.5 space-y-1.5">
          {options.map((o, i) => (
            <li
              key={`${o.airline}-${o.price_eur}-${i}`}
              className={`rounded-lg px-2 py-1.5 ${o.roles.includes("best") ? "bg-signal-soft" : ""}`}
            >
              {/* THREE compact lines, not one. Six-plus pieces of data
                  in a single row needed 432px against roughly 300px of
                  usable width on a phone and pushed the whole page into
                  horizontal scroll. Line 1: what it IS (labels). Line
                  2: what you choose between. Line 3: the detail you
                  check afterwards, plus the action. */}
              {o.roles.length > 0 && (
                <div className="mb-0.5 flex flex-wrap items-center gap-1">
                  {o.roles.map((role) => <RoleBadge key={role} role={role} />)}
                </div>
              )}
              <div className="flex min-w-0 items-baseline gap-2 text-xs">
                <span className="w-12 flex-none font-semibold tabular-nums text-ink">
                  €{Math.round(o.price_eur)}
                </span>
                <span className="min-w-0 flex-1 truncate text-muted">{o.airline}</span>
                <span className="flex-none tabular-nums text-muted">
                  {formatDuration(o.duration_minutes)}
                </span>
                <span className="flex-none text-subtle">
                  {o.stops === 0
                    ? t("flightNonstop")
                    : o.stops === 1
                      ? t("flightOneStop")
                      : t("flightStops", { n: String(o.stops) })}
                </span>
              </div>
              <div className="mt-0.5 flex min-w-0 items-center gap-2 text-[11px] text-subtle">
                <span className="min-w-0 flex-1 truncate">
                  {o.flight_numbers.length > 0 ? o.flight_numbers.join(" · ") : " "}
                </span>
                <span className="flex-none tabular-nums">
                  {t("flightTripTotal", { total: String(Math.round(o.trip_total_eur)) })}
                </span>
                {booking && <BookFlightButton option={o} booking={booking} />}
              </div>
            </li>
          ))}
        </ul>
      )}

      {open && booking && (
        <p className="mt-2 text-[10px] leading-snug text-subtle">{t("flightBookNote")}</p>
      )}
    </div>
  );
}
