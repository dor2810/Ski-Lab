"use client";

import { useTranslation } from "@/lib/i18n/context";
import type { TripResult } from "@/lib/api";
import { FlightIcon, BusIcon, TrainIcon, TransferIcon, SnowMountainIcon } from "./icons";

/**
 * The whole trip door to door, as one line of icons and durations:
 *
 *   ✈ 5h30 → 🚌 4h00 → 🎿 6 nights → 🚌 4h00 → ✈ 5h50
 *
 * The owner's ask, verbatim: "a timeline with logos and time like
 * airplane logo with time of flight length then when arriving then the
 * shuttle like a bus or train logo then the time of the shuttle then
 * something that represents the ski with the duration of the vacation
 * and then again some shuttle and some flight."
 *
 * WHY IT EARNS ITS SPACE: the card already lists flights and transfers
 * as two separate expandable panels, which answers "what can I book"
 * but never "what does the day actually look like". Seeing a 14-hour
 * flight followed by a 4-hour coach in one glance is the fact that
 * changes a decision, and it is currently spread across two lists.
 *
 * HONESTY RULES BAKED IN:
 *  - Every duration shown is a REAL figure from the data. A leg whose
 *    length we do not know renders as a dash, never as a guess and
 *    never silently borrowed from the other direction (the outbound
 *    and return flight are genuinely different lengths -- 21h20 out
 *    and 5h50 back on a real TLV-GVA itinerary).
 *  - The return flight duration only exists for Kiwi-sourced options;
 *    Google's parse has no inbound leg. That leg degrades to a dash.
 *  - The transfer icon follows the actual mode of the cheapest option
 *    (bus / train / private), so it never shows a coach for a taxi.
 *
 * RTL: the app runs Hebrew, and a journey reads in the writing
 * direction. The row is plain flex with logical spacing, so it mirrors
 * with `dir` rather than needing a second layout.
 */

function formatDuration(minutes: number | null | undefined): string | null {
  if (minutes == null || minutes <= 0) return null;
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (!h) return `${m}min`;
  return m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`;
}

function TransferGlyph({ mode, size }: { mode: string | null; size: number }) {
  if (mode === "train") return <TrainIcon size={size} />;
  if (mode === "minivan") return <TransferIcon size={size} />;
  return <BusIcon size={size} />;
}

function Leg({
  icon, label, sub, unknownReason, onOpen, openLabel,
}: {
  icon: React.ReactNode; label: string | null; sub: string;
  /** Open the detail this leg belongs to -- the flight list for a
   *  plane, the transfer list for a coach, the stay for the nights. */
  onOpen?: () => void;
  /** What that jump does, for the tooltip and the accessible name. */
  openLabel?: string;
  // Why this leg has no figure. A bare dash reads as a bug; the
  // reason turns it into information (this provider publishes
  // outbound legs only -- see the component docstring).
  unknownReason?: string;
}) {
  const { t } = useTranslation();
  // The icon is the target: a whole-leg hit area would swallow the
  // duration text, which people select and read.
  const disc = (
    <span className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface text-sky">
      {icon}
    </span>
  );
  return (
    <li className="flex min-w-0 flex-col items-center gap-1 text-center">
      {onOpen ? (
        <button
          type="button"
          onClick={onOpen}
          title={openLabel}
          aria-label={openLabel}
          className="rounded-full transition-colors hover:text-signal focus:outline-none focus-visible:ring-2 focus-visible:ring-signal [&>span]:hover:border-signal"
        >
          {disc}
        </button>
      ) : disc}
      <span
        className={`text-xs font-semibold tabular-nums ${label ? "text-ink" : "cursor-help text-subtle"}`}
        title={label ? undefined : unknownReason}
      >
        {label ?? t("timelineUnknownDuration")}
      </span>
      <span className="text-[10px] leading-tight text-subtle">{sub}</span>
    </li>
  );
}

function Connector() {
  // Decorative only -- the legs carry the meaning, so it is hidden
  // from assistive tech rather than read out as noise.
  return <li aria-hidden="true" className="h-px w-4 flex-none bg-line sm:w-6" />;
}

export function JourneyTimeline({
  result, flightIndex = 0, transferIndex = 0, onNavigate,
}: {
  result: TripResult;
  // WHICH options the timeline describes. Defaults to 0 -- the
  // cheapest of each, which is what the headline price is built from
  // -- but the card passes the user's actual choice, so picking the
  // train instead of the coach redraws the icon and the duration.
  // A timeline that keeps showing the coach after you choose the
  // train is describing a trip nobody selected.
  flightIndex?: number;
  transferIndex?: number;
  /** Open the tab holding this leg's detail, same as the cost lines. */
  onNavigate?: (tab: "getting" | "staying") => void;
}) {
  const { t } = useTranslation();

  const flight = result.flight_options?.[flightIndex] ?? result.flight_options?.[0] ?? null;
  const transfer = result.transfer_options?.[transferIndex] ?? result.transfer_options?.[0] ?? null;

  const nights =
    result.start_date && result.end_date
      ? Math.round(
          (new Date(result.end_date + "T00:00:00").getTime() -
            new Date(result.start_date + "T00:00:00").getTime()) /
            86_400_000
        )
      : null;

  // Nothing real to draw: no flight legs and no stay length. Better an
  // absent timeline than a row of dashes pretending to be a journey.
  if (!flight && nights == null) return null;

  const outbound = formatDuration(flight?.duration_minutes);
  const back = formatDuration(flight?.return_duration_minutes);
  const ride = formatDuration(transfer?.duration_minutes);
  const transferMode = transfer?.mode ?? null;
  const transferLabel = t(
    transferMode === "train" ? "transferModeTrain"
      : transferMode === "minivan" ? "transferModePrivate"
      : "transferModeBus"
  );

  return (
    <section className="mt-4 rounded-xl border border-line bg-sunken/40 px-3 py-3">
      <h4 className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-subtle">
        {t("timelineTitle")}
      </h4>
      {/* Scrolls inside itself on a narrow phone rather than pushing
          the whole card sideways. */}
      <ol className="flex items-start justify-between gap-1 overflow-x-auto">
        <Leg
          icon={<FlightIcon size={16} />}
          label={outbound}
          sub={t("timelineFlightOut")}
          onOpen={onNavigate ? () => onNavigate("getting") : undefined}
          openLabel={t("timelineOpenFlights")}
        />
        <Connector />
        <Leg
          icon={<TransferGlyph mode={transferMode} size={16} />}
          label={ride}
          sub={transferLabel}
          onOpen={onNavigate ? () => onNavigate("getting") : undefined}
          openLabel={t("timelineOpenTransfer")}
        />
        <Connector />
        <Leg
          icon={<SnowMountainIcon size={16} />}
          label={nights != null ? t("timelineNights", { n: String(nights) }) : null}
          sub={result.resort.name}
          onOpen={onNavigate ? () => onNavigate("staying") : undefined}
          openLabel={t("timelineOpenStay")}
        />
        <Connector />
        <Leg
          icon={<TransferGlyph mode={transferMode} size={16} />}
          label={ride}
          sub={transferLabel}
          onOpen={onNavigate ? () => onNavigate("getting") : undefined}
          openLabel={t("timelineOpenTransfer")}
        />
        <Connector />
        <Leg
          icon={<FlightIcon size={16} />}
          label={back}
          sub={t("timelineFlightBack")}
          unknownReason={t("timelineReturnUnknown")}
          onOpen={onNavigate ? () => onNavigate("getting") : undefined}
          openLabel={t("timelineOpenFlights")}
        />
      </ol>
    </section>
  );
}
