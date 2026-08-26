"use client";

import { PriceIcon, CalendarIcon, TrendIcon } from "./icons";
import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";

const PROBLEMS: { icon: typeof CalendarIcon; titleKey: keyof Dictionary; bodyKey: keyof Dictionary }[] = [
  { icon: CalendarIcon, titleKey: "problem1Title", bodyKey: "problem1Body" },
  { icon: PriceIcon, titleKey: "problem2Title", bodyKey: "problem2Body" },
  { icon: TrendIcon, titleKey: "problem3Title", bodyKey: "problem3Body" },
];

export function ProblemSection() {
  const { t } = useTranslation();
  return (
    <section className="mx-auto max-w-5xl px-6 py-20">
      <div className="grid gap-10 sm:grid-cols-3">
        {PROBLEMS.map(({ icon: Icon, titleKey, bodyKey }) => (
          <div key={titleKey} className="text-center sm:text-start">
            <Icon size={28} className="text-sky mb-4 mx-auto sm:mx-0" />
            <h3 className="font-semibold text-lg text-ink mb-2">{t(titleKey)}</h3>
            <p className="text-muted text-sm leading-relaxed">{t(bodyKey)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
