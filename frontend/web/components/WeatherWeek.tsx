"use client";

import { useState } from "react";
import type { TripWeather } from "@/lib/api";
import { formatWeekday } from "@/lib/format";
import { useTranslation } from "@/lib/i18n/context";
import { WeatherIcon, SnowIcon } from "./icons";

// A single day's temperature range, drawn as a vertical bar from
// temp_min_c to temp_max_c, scaled against the WEEK's own observed
// min/max (not a fixed scale) -- so a mild coastal week and a deep-
// freeze week each use the full height of the chart, rather than one
// looking like a flat line against the other's range.
function DayBar({
  day,
  weekMin,
  weekMax,
  locale,
}: {
  day: TripWeather["days"][number];
  weekMin: number;
  weekMax: number;
  locale: string;
}) {
  const { t } = useTranslation();
  const span = Math.max(weekMax - weekMin, 1); // guard against a div-by-zero on a dead-flat week
  const barHeightPct = 100;
  const topPct = ((weekMax - day.temp_max_c) / span) * barHeightPct;
  const bottomPct = ((day.temp_min_c - weekMin) / span) * barHeightPct;
  // The visible bar spans from topPct to (100 - bottomPct) down the track.
  const barTop = Math.max(0, Math.min(100, topPct));
  const barBottom = Math.max(0, Math.min(100, bottomPct));

  return (
    <div className="flex w-16 flex-none flex-col items-center gap-1.5">
      <span className="text-[11px] font-semibold text-ice/70">{formatWeekday(day.date, locale)}</span>
      <span className="text-[10px] tabular-nums text-white">{Math.round(day.temp_max_c)}°</span>
      <div className="relative h-20 w-2 rounded-full bg-white/10">
        <div
          className={`absolute w-2 rounded-full ${day.temp_max_c <= 0 ? "bg-sky" : "bg-amber-300/80"}`}
          style={{ top: `${barTop}%`, bottom: `${barBottom}%` }}
        />
      </div>
      <span className="text-[10px] tabular-nums text-ice/60">{Math.round(day.temp_min_c)}°</span>
      <div className="flex h-4 items-center gap-0.5 text-[10px] text-sky">
        {day.snowfall_cm >= 0.5 ? (
          <>
            <SnowIcon size={10} />
            <span className="tabular-nums">{Math.round(day.snowfall_cm)}</span>
          </>
        ) : null}
      </div>
      {/* A compact dot, not a text badge -- at this column width (64px)
          any translated label ("5-yr average" / "ממוצע 5 שנים") would
          have to truncate illegibly. The full explanation is still
          available on hover/long-press via title. */}
      <span
        className={`h-1.5 w-1.5 rounded-full ${day.is_live_forecast ? "bg-sky" : "bg-ice/40"}`}
        title={
          day.is_live_forecast
            ? t("weatherLiveForecast")
            : t("weatherHistoricalAvg", { years: day.years_sampled ?? "" })
        }
      />
      <span className="sr-only">
        {day.is_live_forecast
          ? t("weatherLiveForecast")
          : t("weatherHistoricalAvg", { years: day.years_sampled ?? "" })}
      </span>
    </div>
  );
}

export function WeatherWeek({ weather }: { weather: TripWeather | null }) {
  const { t, locale } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  if (!weather || weather.days.length === 0) return null;

  const weekMin = Math.min(...weather.days.map((d) => d.temp_min_c));
  const weekMax = Math.max(...weather.days.map((d) => d.temp_max_c));

  return (
    <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <WeatherIcon size={16} className="text-sky" />
          {t("weatherTitle")}
        </div>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="text-xs font-semibold text-sky hover:text-sky/80"
        >
          {expanded ? t("weatherHideDaily") : t("weatherShowDaily")}
        </button>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-3 text-center">
        <div>
          <div className="text-[11px] text-ice/50">{t("weatherAvgHigh")}</div>
          <div className="text-lg font-bold tabular-nums text-white">
            {Math.round(weather.avg_temp_max_c)}°
          </div>
        </div>
        <div>
          <div className="text-[11px] text-ice/50">{t("weatherAvgLow")}</div>
          <div className="text-lg font-bold tabular-nums text-white">
            {Math.round(weather.avg_temp_min_c)}°
          </div>
        </div>
        <div>
          <div className="text-[11px] text-ice/50">{t("weatherAvgSnow")}</div>
          <div className="flex items-center justify-center gap-1 text-lg font-bold tabular-nums text-white">
            <SnowIcon size={14} className="text-sky" />
            {Math.round(weather.avg_snowfall_cm)}
            <span className="text-xs font-normal text-ice/50">cm</span>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="mt-4 flex gap-3 overflow-x-auto border-t border-white/10 pt-4">
          {weather.days.map((d) => (
            <DayBar key={d.date} day={d} weekMin={weekMin} weekMax={weekMax} locale={locale} />
          ))}
        </div>
      )}
    </div>
  );
}
