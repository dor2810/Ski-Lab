"use client";

import { useState } from "react";
import type { TripResult } from "@/lib/api";
import { formatEUR, formatDate, seasonLabel } from "@/lib/format";
import { TerrainBar } from "./TerrainBar";
import {
  FlightIcon,
  TransferIcon,
  StayIcon,
  LiftPassIcon,
  GondolaIcon,
  FoodIcon,
  SnowIcon,
  PinIcon,
} from "./icons";

function LivePill({ live }: { live: boolean }) {
  return live ? (
    <span
      className="ml-1.5 inline-block rounded-full bg-sky/20 px-2 py-0.5 text-[10px] font-bold tracking-wide text-sky align-middle"
      title="Priced from a live source, checked just now"
    >
      LIVE
    </span>
  ) : (
    <span
      className="ml-1.5 inline-block rounded-full bg-ice/10 px-2 py-0.5 text-[10px] font-bold tracking-wide text-ice/60 align-middle"
      title="Estimated from published rates — verify before booking"
    >
      EST.
    </span>
  );
}

const LINE_ITEMS = (r: TripResult) => [
  { icon: FlightIcon, label: "Flight", value: r.cost.flight_eur, live: r.cost.flight_price_is_live },
  { icon: TransferIcon, label: "Transfer", value: r.cost.transfer_eur, live: null },
  {
    icon: StayIcon,
    label: "Accommodation",
    value: r.cost.accommodation_eur,
    live: r.cost.accommodation_price_is_live,
  },
  { icon: LiftPassIcon, label: "Lift pass", value: r.cost.ski_pass_eur, live: null },
  { icon: GondolaIcon, label: "Equipment", value: r.cost.equipment_eur, live: null },
  { icon: FoodIcon, label: "Food", value: r.cost.food_eur, live: null },
];

export function ResultCard({ result }: { result: TripResult }) {
  const [expanded, setExpanded] = useState(false);
  const r = result;
  const scorePct = Math.round(r.score * 100);

  return (
    <article
      className={`animate-rise-in rounded-2xl border p-6 sm:p-7 ${
        r.within_budget
          ? "border-white/10 bg-midnight"
          : "border-amber-400/40 bg-midnight ring-1 ring-amber-400/20"
      }`}
    >
      {!r.within_budget && (
        <div className="mb-4 rounded-lg bg-amber-400/10 px-3 py-2 text-xs font-semibold text-amber-300">
          Over your budget — the cheapest trip we could find. Nothing fit your stated budget.
        </div>
      )}

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white">{r.resort.name}</h3>
          <p className="text-sm text-ice/60">{r.resort.country}</p>
          {r.start_date && r.end_date && (
            <p className="mt-1 text-sm text-sky">
              {formatDate(r.start_date)} – {formatDate(r.end_date)}
              {r.season && (
                <span className="ml-2 rounded bg-white/5 px-1.5 py-0.5 text-[11px] font-semibold text-ice/70">
                  {seasonLabel(r.season)}
                </span>
              )}
            </p>
          )}
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-3xl font-extrabold tabular-nums text-white">
              {formatEUR(r.cost.total_eur)}
            </div>
            <div className="text-xs text-ice/50">per person, total</div>
          </div>
          <div
            className="flex h-12 w-12 flex-none items-center justify-center rounded-full border-2 border-sky/60 text-sm font-bold text-sky"
            title="Match score"
          >
            {scorePct}
          </div>
        </div>
      </div>

      <div className="mt-6 grid grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-3">
        {LINE_ITEMS(r).map(({ icon: Icon, label, value, live }) => (
          <div key={label} className="flex items-center gap-2 text-sm">
            <Icon size={16} className="flex-none text-sky" />
            <span className="text-ice/70">{label}</span>
            <span className="ml-auto font-semibold tabular-nums text-white">
              {formatEUR(value)}
            </span>
            {live !== null && <LivePill live={live} />}
          </div>
        ))}
      </div>

      <div className="mt-6">
        <TerrainBar terrain={r.resort.terrain} />
      </div>

      <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-ice/60">
        <span>{r.resort.piste_km} km piste</span>
        <span className="flex items-center gap-1">
          <PinIcon size={12} /> {Math.round(r.resort.transfer_time_minutes)} min from{" "}
          {r.resort.nearest_airport}
        </span>
        <span>Off-piste {r.resort.off_piste_rating}/5</span>
        <span className="flex items-center gap-1">
          <SnowIcon size={12} /> Snow {r.resort.snow_reliability}/5
        </span>
        <span>Nightlife {r.resort.nightlife_rating}/5</span>
      </div>

      {/* r.explanation already starts with "Why: " (see nlp/explainer.py) -- no need to prepend our own label. */}
      <p className="mt-4 text-sm leading-relaxed text-ice/80">{r.explanation}</p>

      <button
        onClick={() => setExpanded((e) => !e)}
        className="mt-5 text-sm font-semibold text-sky hover:text-sky/80"
      >
        {expanded ? "Hide trip details" : "View trip details"}
      </button>

      {expanded && (
        <div className="mt-4 grid grid-cols-2 gap-x-6 gap-y-1.5 border-t border-white/10 pt-4 text-xs sm:grid-cols-3">
          {Object.entries(r.score_components).map(([dim, val]) => (
            <div key={dim} className="flex justify-between text-ice/60">
              <span className="capitalize">{dim.replace("_", " ")}</span>
              <span className="tabular-nums text-ice/80">{Math.round(val * 100)}%</span>
            </div>
          ))}
          {r.resort.needs_verification && (
            <p className="col-span-full mt-1 text-amber-300/80">
              Some data for this resort is flagged as needing verification.
            </p>
          )}
        </div>
      )}
    </article>
  );
}
