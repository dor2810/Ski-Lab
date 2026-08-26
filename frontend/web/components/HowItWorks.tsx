"use client";

import { PinIcon, TrendIcon, ChartIcon, SnowMountainIcon } from "./icons";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";

const STEPS: { labelKey: keyof Dictionary; icon: typeof PinIcon; bodyKey: keyof Dictionary }[] = [
  { labelKey: "step1Label", icon: PinIcon, bodyKey: "step1Body" },
  { labelKey: "step2Label", icon: TrendIcon, bodyKey: "step2Body" },
  { labelKey: "step3Label", icon: ChartIcon, bodyKey: "step3Body" },
  { labelKey: "step4Label", icon: SnowMountainIcon, bodyKey: "step4Body" },
];

export function HowItWorks() {
  const { t } = useTranslation();
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <h2 className="text-center font-semibold text-2xl sm:text-3xl mb-14">{t("howItWorksTitle")}</h2>
      <div className="grid gap-10 sm:grid-cols-4">
        {STEPS.map(({ labelKey, icon: Icon, bodyKey }, i) => (
          <div key={labelKey} className="relative text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface border border-line">
              <Icon size={24} className="text-sky" />
            </div>
            <div className="text-xs font-bold tracking-widest text-sky mb-1">
              {String(i + 1).padStart(2, "0")} · {t(labelKey)}
            </div>
            <p className="text-muted text-sm leading-relaxed">{t(bodyKey)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
