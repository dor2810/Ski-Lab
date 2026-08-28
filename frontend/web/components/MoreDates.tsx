"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { AlternativeDate } from "@/lib/api";
import { CalendarIcon } from "./icons";
import { formatEUR, formatDate } from "@/lib/format";

/**
 * The per-resort "More dates" expander -- the user's own idea, in
 * their words: "I gave a big time range, a month, and I only got one
 * date for Val Thorens... maybe if I give something this big, I would
 * expect three options."
 *
 * Each alternative comes from a DIFFERENT calendar week of the search
 * window (engine/date_search.spread_alternative_dates), so a month
 * window reads early / mid / late instead of three near-identical
 * copies of the shown date. Totals are the same static-or-live
 * figures the ranking used -- the EST. badge stays honest per row.
 */
export function MoreDates({ resortName, alternatives }: {
  resortName: string;
  alternatives: AlternativeDate[] | undefined;
}) {
  const { t, locale } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!alternatives || alternatives.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-line bg-sunken/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-sky hover:text-sky/80"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <CalendarIcon size={14} className="flex-none" />
          <span className="truncate">
            {t("moreDatesTitle", { resort: resortName, count: String(alternatives.length) })}
          </span>
        </span>
        <span aria-hidden="true" className="text-xs text-subtle">{open ? "−" : "+"}</span>
      </button>

      {open && (
        <>
          <ul className="mt-2.5 space-y-1.5">
            {alternatives.map((a) => (
              <li key={a.start_date} className="rounded-lg px-2 py-1.5">
                <div className="flex min-w-0 items-baseline gap-2 text-xs">
                  <span className="min-w-0 flex-1 truncate font-semibold text-ink">
                    {formatDate(a.start_date, locale)} – {formatDate(a.end_date, locale)}
                  </span>
                  {!a.flight_price_is_live && !a.accommodation_price_is_live && (
                    <span className="flex-none rounded-full border border-line bg-sunken px-1.5 py-px text-[10px] font-semibold text-subtle">
                      {t("estBadge")}
                    </span>
                  )}
                  {!a.within_budget && (
                    <span className="flex-none rounded-full bg-warn-soft px-1.5 py-px text-[10px] font-semibold text-warn">
                      {t("moreDatesOverBudget")}
                    </span>
                  )}
                  <span className="flex-none font-bold tabular-nums text-ink">
                    {formatEUR(a.total_eur, locale)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] leading-snug text-subtle">{t("moreDatesNote")}</p>
        </>
      )}
    </div>
  );
}
