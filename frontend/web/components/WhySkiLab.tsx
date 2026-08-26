"use client";

import { LiftPassIcon, TrendIcon, WeatherIcon, PriceIcon, ConfidenceIcon } from "./icons";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";

const POINTS: { icon: typeof LiftPassIcon; key: keyof Dictionary }[] = [
  { icon: LiftPassIcon, key: "why1" },
  { icon: TrendIcon, key: "why2" },
  { icon: WeatherIcon, key: "why3" },
  { icon: PriceIcon, key: "why4" },
  { icon: ConfidenceIcon, key: "why5" },
];

export function WhySkiLab() {
  const { t } = useTranslation();
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="text-center font-semibold text-2xl sm:text-3xl mb-12">{t("whySkiLabTitle")}</h2>
      <div className="grid gap-8 sm:grid-cols-5">
        {POINTS.map(({ icon: Icon, key }) => (
          <div key={key} className="text-center">
            <Icon size={26} className="mx-auto mb-3 text-sky" />
            <p className="text-sm text-muted">{t(key)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
