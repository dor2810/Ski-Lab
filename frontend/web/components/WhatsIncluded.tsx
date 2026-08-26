"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";

/**
 * What the headline total does and does NOT cover.
 *
 * WHY THIS EXISTS: stating inclusions prominently is the single most
 * repeated trust device across every ski operator studied (Club Med,
 * Crystal, Iglu, SkiDeal, Penguin) -- and we had none of it. We show a
 * cost breakdown and call it "the real total", so a reasonable person
 * assumes it is complete. It isn't: lift lessons, ski-baggage fees,
 * insurance, resort tax and lunch on the mountain are all real money we
 * don't count. Saying so plainly is the difference between a number a
 * user can trust and one that quietly embarrasses us at the airport.
 *
 * The excluded items are deliberately SPECIFIC and sourced rather than
 * vague hedging:
 *  - Ski lessons: group courses run roughly EUR100/week (Bulgaria) to
 *    EUR414/week (major French resorts).
 *  - Ski baggage: researched per airline 2026-08-27. Legacy carriers
 *    (Lufthansa/SWISS/Austrian, El Al, Air France/KLM) carry one ski set
 *    FREE above the normal allowance -- but NOT on their cheapest
 *    "Light"/"Basic" fares. Low-cost carriers charge ~EUR42-45 per
 *    flight (Ryanair EUR45, easyJet GBP42). We deliberately do NOT put a
 *    single number in the total, because the fee depends on the fare
 *    class our flight quote actually priced, which the adapter does not
 *    report -- inventing one figure would be wrong in one direction for
 *    half of all users.
 */

const INCLUDED: (keyof Dictionary)[] = [
  "inclFlight",
  "inclTransfer",
  "inclAccommodation",
  "inclLiftPass",
  "inclEquipment",
  "inclFood",
];

const EXCLUDED: (keyof Dictionary)[] = [
  "exclLessons",
  "exclSkiBaggage",
  "exclInsurance",
  "exclResortTax",
  "exclOnMountainLunch",
];

export function WhatsIncluded() {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-4 rounded-xl border border-line bg-sunken/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between text-sm font-semibold text-sky hover:text-sky/80"
      >
        <span>{t("whatsIncludedTitle")}</span>
        <span aria-hidden="true" className="text-xs text-subtle">
          {open ? "−" : "+"}
        </span>
      </button>

      {open && (
        <div className="mt-3 grid gap-4 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-subtle">
              {t("includedHeading")}
            </p>
            <ul className="space-y-1">
              {INCLUDED.map((k) => (
                <li key={k} className="flex items-start gap-1.5 text-xs text-muted">
                  <span aria-hidden="true" className="mt-px font-bold text-piste-beginner">✓</span>
                  {t(k)}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-subtle">
              {t("notIncludedHeading")}
            </p>
            <ul className="space-y-1">
              {EXCLUDED.map((k) => (
                <li key={k} className="flex items-start gap-1.5 text-xs text-muted">
                  <span aria-hidden="true" className="mt-px font-bold text-warn">–</span>
                  {t(k)}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
