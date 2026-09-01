"use client";

import { useEffect, useRef, useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import { miscFor } from "@/lib/tripTotal";
import type { CostBreakdown, TripResult } from "@/lib/api";
import type { Dictionary } from "@/lib/i18n/languages";
import { formatEUR } from "@/lib/format";
import {
  FlightIcon, TransferIcon, StayIcon, LiftPassIcon, GondolaIcon, FoodIcon, PriceIcon,
} from "./icons";

/**
 * THE COST INSTRUMENT -- the product's whole differentiator, made
 * visible instead of merely listed.
 *
 * WHAT IT REPLACED and why: the breakdown used to be a six-cell text
 * grid with the total floating separately in the card header. You
 * could read the numbers but never SEE them -- nothing showed that on
 * a real Bansko trip the lift pass (EUR305) is the single biggest
 * line, larger than the flight. Every competitor hides this; showing
 * it is the point of Ski Lab, so it earns the strongest visual
 * treatment on the card.
 *
 * SEVEN SEGMENTS, NOT SIX. The brief said six numbers summing to a
 * total, but the engine's total genuinely includes a 5% misc buffer
 * (verified against the API: 281+102+546+330.32+110+288+82.87 =
 * 1740.19 = total_eur, exactly). Showing six and claiming they sum
 * would be a lie of exactly the kind this project forbids, so the
 * buffer is a labelled seventh segment.
 *
 * COLOUR: a single blue->cyan ramp, deliberately NOT the piste
 * palette. Green/blue/red/black are reserved for terrain difficulty
 * (a real-world standard) and must never be repurposed for cost.
 * Width carries magnitude; colour only separates neighbours, so the
 * chart is still readable in greyscale.
 *
 * ACCESSIBILITY: the bar is aria-hidden decoration -- every figure it
 * encodes is present as text in the itemised list beneath, which is
 * the accessible source of truth. Colour is never the sole carrier:
 * each row pairs its swatch with a written label and amount.
 */

/** Handoff links a cost line can point the traveller at. */
export type FlashTarget = "skiPass" | "equipment";

type Line = {
  key: keyof Dictionary;
  amount: number;
  colour: string;
  icon: typeof FlightIcon;
  source: "live" | "researched" | null;
  /** Handoff link to call out on arrival -- for lines whose
   *  next step is a partner site, not a list on the card. */
  flash?: FlashTarget;
  /** Which evidence tab this line's detail lives in, if any. Rows
   *  with a target become buttons: the breakdown doubles as the
   *  card's table of contents. */
  target?: "getting" | "staying";
};

//: The engine adds a 5% buffer on top of the other lines and rescales
//: it whenever a live price is swapped in (see cost_calculator.
//: apply_live_flight_price). Mirrored here so that choosing a
//: different flight moves the buffer exactly as the backend would,
//: and the seven parts still sum to the displayed total.

// Fixed order, not sorted by size: two cards side by side must be
// comparable line-for-line, and a segment that jumps position between
// resorts destroys that. The largest line is called out in words
// instead (see `biggest` below).
function lines(
  cost: CostBreakdown, flightEur: number, transferEur: number, stayEur: number,
): Line[] {
  // Swapping a flight, transfer or property moves the buffer with it,
  // exactly as the engine's apply_live_*_price helpers do (each adds
  // delta * MISC_COST_RATE), so the parts keep summing to the total.
  const misc = miscFor(cost, { flightEur, transferEur, stayEur });
  return [
    { key: "lineFlight", amount: flightEur, colour: "#1e3a8a", icon: FlightIcon,
      source: cost.flight_price_is_live ? "live" : null, target: "getting" },
    { key: "lineTransfer", amount: transferEur, colour: "#1d4ed8", icon: TransferIcon,
      source: cost.transfer_price_is_live ? "live" : null, target: "getting" },
    { key: "lineAccommodation", amount: stayEur, colour: "#2563eb", icon: StayIcon,
      source: cost.accommodation_price_is_live ? "live" : null, target: "staying" },
    { key: "lineLiftPass", amount: cost.ski_pass_eur, colour: "#0284c7", icon: LiftPassIcon,
      source: cost.ski_pass_price_is_researched ? "researched" : null, target: "staying",
      flash: "skiPass" },
    { key: "lineEquipment", amount: cost.equipment_eur, colour: "#0ea5e9", icon: GondolaIcon,
      source: null, target: "staying", flash: "equipment" },
    { key: "lineFood", amount: cost.food_eur, colour: "#38bdf8", icon: FoodIcon, source: null },
    { key: "lineBuffer", amount: Math.max(0, misc), colour: "#bae6fd", icon: PriceIcon, source: null },
  ];
}

function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const q = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(q.matches);
    const on = () => setReduced(q.matches);
    q.addEventListener("change", on);
    return () => q.removeEventListener("change", on);
  }, []);
  return reduced;
}

/** Counts to `value` once, on mount. The total is the one number worth
 *  animating -- doing it to all seven rows would be decoration. */
function useCountUp(value: number, enabled: boolean) {
  const [shown, setShown] = useState(enabled ? 0 : value);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    if (!enabled) { setShown(value); return; }
    const start = performance.now();
    const DURATION = 650;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / DURATION);
      // Ease-out: fast then settling, so it reads as a machine
      // resolving a figure rather than a slot machine spinning.
      setShown(value * (1 - Math.pow(1 - t, 3)));
      if (t < 1) raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [value, enabled]);
  return shown;
}

function SourcePill({ kind }: { kind: "live" | "researched" }) {
  const { t } = useTranslation();
  const live = kind === "live";
  return (
    <span
      className={`ms-1.5 inline-block flex-none rounded-full px-1.5 py-px text-[9px] font-bold uppercase tracking-wide align-middle ${
        live ? "bg-sky/15 text-sky" : "bg-signal-soft text-signal"
      }`}
      title={t(live ? "liveTooltip" : "researchedTooltip")}
    >
      {t(live ? "liveBadge" : "researchedBadge")}
    </span>
  );
}

export function CostInstrument({
  result, flightIndex = 0, transferIndex = 0, stayIndex = 0, onNavigate,
}: {
  result: TripResult;
  // The chosen options drive the numbers. Index 0 is the cheapest of
  // each, which is what the API's own cost lines were built from --
  // verified against real payloads that flight_options[0].price_eur
  // equals cost.flight_eur exactly, so the default shows the
  // backend's figures with no drift.
  flightIndex?: number;
  transferIndex?: number;
  stayIndex?: number;
  /** Jump to the evidence for a line. Makes the breakdown the card's
   *  table of contents rather than a dead-end summary. */
  onNavigate?: (tab: "getting" | "staying", flash?: FlashTarget) => void;
}) {
  const { t, locale } = useTranslation();
  const reduced = usePrefersReducedMotion();
  const [mounted, setMounted] = useState(false);
  const [active, setActive] = useState<number | null>(null);

  useEffect(() => {
    // One frame later so the browser paints zero-width segments first
    // and then transitions them -- otherwise there is nothing to ease.
    const id = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(id);
  }, []);

  const chosenFlight = result.flight_options?.[flightIndex];
  const chosenTransfer = result.transfer_options?.[transferIndex];
  const chosenStay = result.accommodation_options?.[stayIndex];
  const items = lines(
    result.cost,
    chosenFlight ? chosenFlight.price_eur : result.cost.flight_eur,
    chosenTransfer ? chosenTransfer.price_eur_per_person : result.cost.transfer_eur,
    chosenStay ? chosenStay.per_person_eur : result.cost.accommodation_eur,
  );
  // Summed from the parts shown, never taken separately -- the whole
  // point of this panel is that the total IS the sum of these rows.
  const total = items.reduce((sum, l) => sum + l.amount, 0);
  const counted = useCountUp(total, !reduced);
  const biggest = items.reduce((a, b) => (b.amount > a.amount ? b : a), items[0]);
  const pct = (n: number) => (total > 0 ? (n / total) * 100 : 0);

  return (
    <section className="mt-5 rounded-xl border border-line bg-surface p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h4 className="text-[11px] font-semibold uppercase tracking-wide text-subtle">
          {t("costInstrumentTitle")}
        </h4>
        <p className="text-[11px] text-subtle">
          {t("costInstrumentBiggest", { line: t(biggest.key) })}
        </p>
      </div>

      {/* THE BAR carries the hero weight, not the total: the point is
          watching parts ASSEMBLE into a sum. Tall enough to label the
          large segments in place, so the biggest costs are readable
          without cross-referencing the list. */}
      <div
        aria-hidden="true"
        className="mt-3 flex h-11 w-full overflow-hidden rounded-lg bg-sunken"
      >
        {items.map((line, i) => {
          const share = pct(line.amount);
          const navigable = Boolean(line.target && onNavigate);
          return (
            // Clickable, but deliberately NOT focusable: the bar stays
            // aria-hidden because the table below already carries the
            // same figures, and that table's row buttons are the
            // labelled, keyboard-reachable way to the same detail.
            // This is a pointer shortcut on a duplicate, not the only
            // route to it.
            <span
              key={line.key}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              onClick={navigable ? () => onNavigate!(line.target!, line.flash) : undefined}
              className={`flex h-full items-center justify-center transition-[width,opacity] duration-700 ease-out ${
                navigable ? "cursor-pointer" : ""
              }`}
              style={{
                width: mounted ? `${share}%` : "0%",
                backgroundColor: line.colour,
                transitionDelay: reduced ? "0ms" : `${i * 70}ms`,
                opacity: active === null || active === i ? 1 : 0.32,
              }}
            >
              {/* Only where it genuinely fits -- a clipped label is
                  worse than none. */}
              {share >= 12 && (
                <span className="px-1 text-[10px] font-bold tabular-nums text-white/95">
                  {Math.round(share)}%
                </span>
              )}
            </span>
          );
        })}
      </div>

      {/* ONE aligned table. Single column on purpose: two columns put
          the amounts in two different right edges, which is exactly
          what stops a cost breakdown reading as an instrument. */}
      <ul className="mt-4 divide-y divide-line/70">
        {items.map((line, i) => {
          const Icon = line.icon;
          return (
            <li
              key={line.key}
              onMouseEnter={() => setActive(i)}
              onMouseLeave={() => setActive(null)}
              className={`flex items-center gap-2 py-1.5 transition-colors sm:gap-3 ${
                active === i ? "bg-sunken" : ""
              }`}
            >
              {/* The icon IS the key -- tinted with its segment colour,
                  so one token does the job two were doing. */}
              <Icon size={15} className="flex-none" style={{ color: line.colour }} />
              {line.target && onNavigate ? (
                <button
                  type="button"
                  onClick={() => onNavigate(line.target!, line.flash)}
                  className="block min-w-0 flex-1 rounded text-start text-sm text-muted underline decoration-line underline-offset-4 hover:text-signal hover:decoration-signal focus:outline-none focus-visible:ring-2 focus-visible:ring-signal"
                  title={t("costInstrumentOpenDetail", { line: t(line.key) })}
                >
                  {t(line.key)}
                </button>
              ) : (
                <span className="min-w-0 flex-1 text-sm text-muted">{t(line.key)}</span>
              )}
              {line.source && <SourcePill kind={line.source} />}
              <span className="w-16 flex-none text-end text-sm font-semibold tabular-nums text-ink sm:w-20">
                {formatEUR(line.amount, locale)}
              </span>
              <span className="hidden w-8 flex-none text-end text-xs tabular-nums text-subtle sm:block sm:w-10">
                {Math.round(pct(line.amount))}%
              </span>
            </li>
          );
        })}
        {/* The total sits at the foot of the same column the parts are
            in, so the sum is visibly the sum OF them. */}
        <li className="flex items-center gap-2 border-t-2 border-ink/15 pt-2.5 sm:gap-3">
          <span className="min-w-0 flex-1 text-sm font-semibold text-ink">
            {t("costInstrumentTotalLabel")}
          </span>
          <span className="w-16 flex-none text-end text-xl font-extrabold tabular-nums text-ink sm:w-20">
            {formatEUR(counted, locale)}
          </span>
          <span className="hidden w-8 flex-none sm:block sm:w-10" />
        </li>
      </ul>
    </section>
  );
}
