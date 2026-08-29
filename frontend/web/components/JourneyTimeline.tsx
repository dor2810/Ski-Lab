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
  icon, label, sub,
}: { icon: React.ReactNode; label: string | null; sub: string }) {
  const { t } = useTranslation();
  return (
    <li className="flex min-w-0 flex-col items-center gap-1 text-center">
      <span className="flex h-9 w-9 items-center justify-center rounded-full border border-line bg-surface text-sky">
        {icon}
      </span>
      <span className="text-xs font-semibold tabular-nums text-ink">
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

export function JourneyTimeline({ result }: { result: TripResult }) {
  const { t } = useTranslation();

  // Anchored on the options the headline price is actually built from:
  // flight_options is cheapest-first (engine/flight_picks) and so is
  // transfer_options (engine/transfer_options), so [0] is the trip we
  // are quoting -- not a different, prettier one.
  const flight = result.flight_options?.[0] ?? null;
  const transfer = result.transfer_options?.[0] ?? null;

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
        <Leg icon={<FlightIcon size={16} />} label={outbound} sub={t("timelineFlightOut")} />
        <Connector />
        <Leg
          icon={<TransferGlyph mode={transferMode} size={16} />}
          label={ride}
          sub={transferLabel}
        />
        <Connector />
        <Leg
          icon={<SnowMountainIcon size={16} />}
          label={nights != null ? t("timelineNights", { n: String(nights) }) : null}
          sub={result.resort.name}
        />
        <Connector />
        <Leg
          icon={<TransferGlyph mode={transferMode} size={16} />}
          label={ride}
          sub={transferLabel}
        />
        <Connector />
        <Leg icon={<FlightIcon size={16} />} label={back} sub={t("timelineFlightBack")} />
      </ol>
    </section>
  );
}
