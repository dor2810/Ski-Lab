"use client";

import { useTranslation } from "@/lib/i18n/context";
import type { Dictionary } from "@/lib/i18n/languages";

/**
 * No real mountain photograph asset was supplied (frontend/images only
 * contains the logo and a brand style-reference sheet, not usable
 * photography) -- rather than hotlink an unvetted external stock photo,
 * the hero is built from a soft sky-to-snow gradient with a hand-drawn
 * line-art mountain range. Swap in a real photo later by dropping a
 * file in public/images and changing this section's background.
 *
 * Light-theme rework (2026-08-27): the gradient now reads as daylight
 * over snow rather than night over navy, and the ridge lines are drawn
 * as FILLED, receding layers instead of bare strokes -- on a light
 * canvas, thin strokes on their own look like an unfinished wireframe,
 * while stacked translucent fills give real depth. The trust strip at
 * the bottom is new: the single most common reason a hesitant visitor
 * bounces is not knowing whether the numbers are real, so it answers
 * that before they scroll.
 */
const TRUST_KEYS = ["heroTrustLive", "heroTrustTotal", "heroTrustFree"] as const satisfies readonly (keyof Dictionary)[];

export function Hero({ onPlanTrip }: { onPlanTrip: () => void }) {
  const { t } = useTranslation();
  return (
    <section className="relative overflow-hidden">
      <div
        className="absolute inset-0"
        style={{
          background:
            "linear-gradient(180deg, #dbeafe 0%, #eaf2fb 38%, var(--color-canvas) 78%)",
        }}
      />
      <MountainRange />

      <div className="relative mx-auto max-w-5xl px-6 pt-16 pb-24 sm:pt-24 sm:pb-32 text-center">
        <h1 className="font-extrabold leading-[1.05] text-5xl sm:text-6xl lg:text-7xl tracking-tight text-ink">
          {t("heroHeadline1")}
          <br />
          <span className="font-semibold text-signal">{t("heroHeadline2")}</span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-muted max-w-2xl mx-auto">
          {t("heroSubhead")}
        </p>

        <div className="mt-10 flex items-center justify-center">
          <button
            onClick={onPlanTrip}
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-signal hover:bg-signal/90 transition-colors font-semibold text-white shadow-lg shadow-signal/25"
          >
            {t("heroCta")}
          </button>
        </div>

        {/* Answers "are these numbers real?" before the visitor has to
            ask. Each item is a claim this project can actually back up. */}
        {/* `as const` keeps these literal, so a typo is a BUILD error --
            the earlier version cast to one key type, which silently
            defeated exactly the compile-time guarantee lib/i18n/
            languages.ts exists to provide. */}
        <ul className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-sm text-muted">
          {TRUST_KEYS.map((k) => (
            <li key={k} className="flex items-center gap-2">
              <CheckIcon />
              {t(k)}
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

function CheckIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true" className="flex-none">
      <circle cx="8" cy="8" r="8" className="fill-signal/12" />
      <path
        d="M4.6 8.2l2.2 2.2 4.6-4.6"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-signal"
      />
    </svg>
  );
}

function MountainRange() {
  return (
    <svg
      className="absolute inset-x-0 bottom-0 w-full"
      viewBox="0 0 1440 300"
      fill="none"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      {/* Farthest ridge -- palest, least contrast, reads as distance. */}
      <path
        d="M0 300 L0 176 L190 96 L328 168 L470 60 L610 158 L742 84 L900 186 L1046 74 L1206 152 L1330 108 L1440 190 L1440 300 Z"
        fill="var(--color-signal)"
        opacity="0.10"
      />
      {/* Middle ridge. */}
      <path
        d="M0 300 L0 226 L150 158 L300 220 L438 138 L580 224 L720 150 L880 236 L1020 148 L1180 222 L1320 168 L1440 232 L1440 300 Z"
        fill="var(--color-signal)"
        opacity="0.16"
      />
      {/* Nearest ridge -- strongest, anchors the section to the page. */}
      <path
        d="M0 300 L0 268 L180 214 L360 264 L520 200 L680 262 L840 208 L1010 268 L1180 214 L1330 256 L1440 224 L1440 300 Z"
        fill="var(--color-signal)"
        opacity="0.22"
      />
      {/* A single crisp summit stroke, the one line-art element kept from
          the dark theme -- it echoes the logo's survey line. */}
      <path
        d="M470 60 L610 158 L742 84"
        stroke="var(--color-signal)"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        opacity="0.45"
      />
    </svg>
  );
}
