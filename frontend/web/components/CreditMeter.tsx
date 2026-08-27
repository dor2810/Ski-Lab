"use client";

import { useTranslation } from "@/lib/i18n/context";
import type { Credits } from "@/lib/api";

/**
 * Today's remaining search credits, and what the search about to be run
 * will cost.
 *
 * WHY SHOW THE COST BEFORE THE SEARCH: a limit a user only discovers by
 * hitting it feels like a malfunction. Quoting it up front turns the
 * same restriction into an understandable trade -- and it makes the
 * pricing rule teach itself, because the user watches the number rise
 * as they widen the date range.
 *
 * The bar is deliberately calm until it isn't: neutral while there's
 * plenty left, and only turning to the warning colour when a real
 * decision is approaching. A meter that looks alarming at 90% remaining
 * trains people to ignore it.
 */
const LOW_FRACTION = 0.2;

export function CreditMeter({
  credits,
  pendingCost,
}: {
  credits: Credits | null;
  pendingCost: number | null;
}) {
  const { t } = useTranslation();
  if (!credits) return null;

  const { remaining, daily_allowance: allowance } = credits;
  const fraction = allowance > 0 ? remaining / allowance : 0;
  const low = fraction <= LOW_FRACTION;
  const cannotAfford = pendingCost !== null && pendingCost > remaining;

  return (
    <div className="rounded-xl border border-line bg-sunken/60 p-3">
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-subtle">
          {t("creditsLabel")}
        </span>
        <span
          className={`text-xs font-semibold tabular-nums ${
            low ? "text-warn" : "text-muted"
          }`}
        >
          {t("creditsRemaining", { remaining: String(remaining), allowance: String(allowance) })}
        </span>
      </div>

      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-line"
        role="progressbar"
        aria-valuenow={remaining}
        aria-valuemin={0}
        aria-valuemax={allowance}
      >
        <div
          className={`h-full rounded-full transition-[width] ${low ? "bg-warn" : "bg-signal"}`}
          style={{ width: `${Math.max(0, Math.min(100, fraction * 100))}%` }}
        />
      </div>

      {pendingCost !== null && (
        <p className={`mt-1.5 text-[11px] ${cannotAfford ? "text-warn" : "text-subtle"}`}>
          {cannotAfford
            ? t("creditsNotEnough", { cost: String(pendingCost) })
            : t("creditsThisSearch", { cost: String(pendingCost) })}
        </p>
      )}
    </div>
  );
}
