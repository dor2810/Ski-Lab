"use client";

export type RawWeights = {
  ski_quality: number;
  price: number;
  snow: number;
  nightlife: number;
  convenience: number;
  accommodation: number;
};

export const DEFAULT_RAW_WEIGHTS: RawWeights = {
  ski_quality: 30,
  price: 20,
  snow: 15,
  nightlife: 15,
  convenience: 10,
  accommodation: 10,
};

const LABELS: Record<keyof RawWeights, string> = {
  ski_quality: "Ski quality",
  price: "Price",
  snow: "Snow reliability",
  nightlife: "Nightlife",
  convenience: "Convenience",
  accommodation: "Accommodation comfort",
};

/** Sliders don't need to individually sum to 100 -- the displayed % for
 * each is its live share of the total, so the SET always reads as 100%
 * even though the underlying raw values are just relative weights. */
export function normalizePercent(raw: RawWeights, key: keyof RawWeights): number {
  const sum = Object.values(raw).reduce((a, b) => a + b, 0);
  if (sum <= 0) return 0;
  return Math.round((raw[key] / sum) * 100);
}

export function normalizeWeights(raw: RawWeights) {
  const sum = Object.values(raw).reduce((a, b) => a + b, 0) || 1;
  return Object.fromEntries(
    Object.entries(raw).map(([k, v]) => [k, v / sum])
  ) as RawWeights;
}

export function PrioritySliders({
  value,
  onChange,
}: {
  value: RawWeights;
  onChange: (next: RawWeights) => void;
}) {
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {(Object.keys(LABELS) as (keyof RawWeights)[]).map((key) => (
        <div key={key}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <label htmlFor={`slider-${key}`} className="font-medium text-ice/80">
              {LABELS[key]}
            </label>
            <span className="tabular-nums font-bold text-sky">
              {normalizePercent(value, key)}%
            </span>
          </div>
          <input
            id={`slider-${key}`}
            type="range"
            min={0}
            max={100}
            value={value[key]}
            onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) })}
            className="w-full"
            aria-valuetext={`${normalizePercent(value, key)}%`}
          />
        </div>
      ))}
    </div>
  );
}
