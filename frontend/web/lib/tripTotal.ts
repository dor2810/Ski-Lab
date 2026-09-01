import type { CostBreakdown } from "./api";

/**
 * What a trip costs per person once the traveller has swapped in a
 * different flight, transfer or property.
 *
 * WHY THIS EXISTS: every option the API returns carries its own
 * `trip_total_eur`, but that figure is computed with every OTHER
 * choice left at its default. Once the card let people choose a
 * flight AND a transfer AND a property, those static totals started
 * contradicting the card: picking the fastest flight moved the card to
 * EUR1,170 while the selected stay row still read "whole trip EUR975".
 *
 * The arithmetic mirrors the engine exactly -- cost_calculator's
 * apply_live_flight_price / _transfer_ / _accommodation_ each swap one
 * line and move the buffer by delta * MISC_COST_RATE -- so with every
 * selection at its default this reproduces the API's own numbers
 * rather than competing with them.
 */

/** cost_calculator.MISC_COST_RATE -- keep the two in step. */
export const MISC_RATE = 0.05;

export interface Selection {
  flightEur: number;
  transferEur: number;
  stayEur: number;
}

/** The misc buffer, resized for the current choices. */
export function miscFor(cost: CostBreakdown, sel: Selection): number {
  return cost.misc_eur
    + (sel.flightEur - cost.flight_eur) * MISC_RATE
    + (sel.transferEur - cost.transfer_eur) * MISC_RATE
    + (sel.stayEur - cost.accommodation_eur) * MISC_RATE;
}

export function tripTotalWith(cost: CostBreakdown, sel: Selection): number {
  return sel.flightEur + sel.transferEur + sel.stayEur
    + cost.ski_pass_eur + cost.equipment_eur + cost.food_eur
    + Math.max(0, miscFor(cost, sel));
}
