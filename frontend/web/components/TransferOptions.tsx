"use client";

import { useState } from "react";
import { useTranslation } from "@/lib/i18n/context";
import type { TransferOption } from "@/lib/api";
import type { Dictionary } from "@/lib/i18n/languages";
import { TransferIcon, ExternalLinkIcon } from "./icons";

/**
 * The real ways to get from the arrival airport to the resort --
 * deliberately the same shape as FlightOptions, at the owner's request
 * ("improve the UI of the transfer results. to be like flight
 * options... i want it to be as stable as the flights").
 *
 * WHY THIS REPLACED a single price plus a "cheaper option" footnote:
 * a transfer is a CHOICE, not a fact. On Geneva -> Val Thorens the
 * real spread is a EUR160 round-trip coach seat against a EUR475
 * private minivan -- a 3x decision the old UI mentioned in small grey
 * text while the expensive number drove the total. Now every option is
 * listed, priced per person so they are comparable, and the cheapest
 * one sets the trip cost.
 *
 * Roles reuse the flight vocabulary (Cheapest / Fastest) because
 * travellers already read it, and an option holding both is shown ONCE
 * with both badges.
 */

const MODE_LABEL_KEYS: Record<string, keyof Dictionary> = {
  bus: "transferModeBus",
  train: "transferModeTrain",
  ferry: "transferModeFerry",
  minivan: "transferModePrivate",
};

function formatDuration(minutes: number | null | undefined): string {
  if (minutes == null) return "";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? (m ? `${h}h${String(m).padStart(2, "0")}` : `${h}h`) : `${m}min`;
}

function departureClock(iso: string | null | undefined): string {
  if (!iso) return "";
  // Provider-local time, sliced rather than parsed: `new Date()` would
  // re-render it in the VIEWER's timezone, so a 13:15 coach from Geneva
  // would read 14:15 to someone in Tel Aviv -- the wrong number for
  // catching it.
  const match = iso.match(/T(\d{2}:\d{2})/);
  return match ? match[1] : "";
}

function RoleBadge({ role }: { role: string }) {
  const { t } = useTranslation();
  const label =
    role === "cheapest" ? t("flightRoleCheapest")
    : role === "fastest" ? t("flightRoleFastest")
    : null;
  if (!label) return null;
  const tone = role === "cheapest"
    ? "bg-signal text-white"
    : "bg-sunken text-muted border border-line";
  return (
    <span className={`rounded-full px-1.5 py-px text-[10px] font-semibold uppercase tracking-wide ${tone}`}>
      {label}
    </span>
  );
}

export function TransferOptions({ options }: { options: TransferOption[] }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);

  if (!options || options.length === 0) return null;

  const cheapest = options[0];
  const privateOnly = options.every((o) => o.kind === "private");

  return (
    <div className="mt-3 rounded-xl border border-line bg-sunken/60 p-3">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-sm font-semibold text-sky hover:text-sky/80"
      >
        <span className="flex min-w-0 items-center gap-1.5">
          <TransferIcon size={14} className="flex-none" />
          <span className="truncate">
            {t("transferOptionsTitle", { count: String(options.length) })}
          </span>
        </span>
        <span aria-hidden="true" className="text-xs text-subtle">{open ? "−" : "+"}</span>
      </button>

      {/* The headline trade-off, visible without expanding: what the
          cheapest way actually costs and what kind of thing it is. */}
      <p className="mt-1.5 text-[11px] leading-snug text-muted">
        {t("transferCheapestSummary", {
          price: String(Math.round(cheapest.price_eur_per_person)),
          kind: t(MODE_LABEL_KEYS[cheapest.mode] ?? "transferModePrivate"),
        })}
        {privateOnly && ` ${t("transferPrivateOnlyNote")}`}
      </p>

      {open && (
        <>
          <ul className="mt-2.5 space-y-1.5">
            {options.map((o, i) => (
              <li
                key={`${o.kind}-${o.mode}-${o.price_eur_per_person}-${i}`}
                className={`rounded-lg px-2 py-1.5 ${o.roles.includes("cheapest") ? "bg-signal-soft" : ""}`}
              >
                {o.roles.length > 0 && (
                  <div className="mb-0.5 flex flex-wrap items-center gap-1">
                    {o.roles.map((role) => <RoleBadge key={role} role={role} />)}
                  </div>
                )}
                {/* Three compact lines, same as FlightOptions: what it
                    costs, what it is, then the detail and the action --
                    six data points in one row overflowed a 390px phone. */}
                <div className="flex min-w-0 items-baseline gap-2 text-xs">
                  {/* A range for indicative routes, a single figure
                      for a real quote -- the difference between "buses
                      cost roughly this" and "this is your price". */}
                  <span className="flex-none font-semibold tabular-nums text-ink">
                    €{Math.round(o.price_eur_per_person)}
                    {o.is_indicative && o.price_high_eur_per_person != null
                      ? `–${Math.round(o.price_high_eur_per_person)}` : ""}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-muted">
                    {t(MODE_LABEL_KEYS[o.mode] ?? "transferModePrivate")}
                    {o.carrier ? ` · ${o.carrier}` : ""}
                  </span>
                  {o.duration_minutes != null && (
                    <span className="flex-none tabular-nums text-muted">
                      {formatDuration(o.duration_minutes)}
                    </span>
                  )}
                </div>
                <div className="mt-0.5 flex min-w-0 items-center gap-2 text-[11px] text-subtle">
                  <span className="min-w-0 flex-1 truncate">
                    {o.departure ? t("transferDeparts", { time: departureClock(o.departure) }) : " "}
                  </span>
                  {/* Round trip vs one way is load-bearing: comparing a
                      one-way seat against a return van would flatter
                      the seat by half. */}
                  <span className="flex-none">
                    {o.is_indicative
                      ? t("transferIndicative")
                      : o.is_round_trip ? t("transferReturnIncluded") : t("transferOneWayOnly")}
                  </span>
                  {o.booking_url && (
                    <a
                      href={o.booking_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex flex-none items-center gap-1 rounded-md bg-signal-soft px-2 py-0.5 font-semibold text-signal hover:bg-signal hover:text-white"
                    >
                      {t("transferBook")}
                      <ExternalLinkIcon size={10} className="opacity-70" />
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2 text-[10px] leading-snug text-subtle">
            {t("transferOptionsNote")}
          </p>
        </>
      )}
    </div>
  );
}
