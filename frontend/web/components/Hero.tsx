"use client";

import { Logo } from "./Logo";
import { useTranslation } from "@/lib/i18n/context";

/**
 * No real mountain photograph asset was supplied (frontend/images only
 * contains the logo and a brand style-reference sheet, not usable
 * photography) -- rather than hotlink an unvetted external stock photo,
 * the hero is built as a dark gradient with a hand-drawn line-art
 * mountain range, matching the "instrument panel, not travel brochure"
 * brief instead of faking a photo that isn't there. Swap in a real
 * photo later by dropping a file in public/images and changing this
 * section's background.
 */
export function Hero({ onPlanTrip }: { onPlanTrip: () => void }) {
  const { t } = useTranslation();
  return (
    <section className="relative overflow-hidden">
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse 120% 80% at 50% -10%, #1c2541 0%, #0b1320 60%)",
        }}
      />
      <MountainLines />

      <div className="relative mx-auto max-w-5xl px-6 pt-10 pb-28 sm:pt-14 sm:pb-36 text-center">
        <div className="flex items-center justify-center gap-3 mb-10">
          <Logo size={40} />
          <span className="font-extrabold tracking-widest text-lg">
            SKI <span className="text-sky">LAB</span>
          </span>
        </div>

        <h1 className="font-extrabold leading-[1.05] text-5xl sm:text-6xl lg:text-7xl tracking-tight">
          {t("heroHeadline1")}
          <br />
          <span className="font-semibold text-ice/90">{t("heroHeadline2")}</span>
        </h1>

        <p className="mt-6 text-lg sm:text-xl text-ice/80 max-w-2xl mx-auto">
          {t("heroSubhead")}
        </p>

        <div className="mt-10 flex items-center justify-center">
          <button
            onClick={onPlanTrip}
            className="w-full sm:w-auto px-8 py-4 rounded-xl bg-signal hover:bg-signal/90 transition-colors font-semibold text-white shadow-lg shadow-signal/20"
          >
            {t("heroCta")}
          </button>
        </div>
      </div>
    </section>
  );
}

function MountainLines() {
  return (
    <svg
      className="absolute inset-x-0 bottom-0 w-full text-sky/25"
      viewBox="0 0 1440 260"
      fill="none"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 220 L180 90 L300 170 L420 40 L560 160 L700 70 L860 190 L1000 60 L1160 150 L1300 100 L1440 200"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path
        d="M0 250 L220 150 L380 210 L520 120 L680 220 L840 140 L1000 230 L1180 130 L1440 240"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        className="text-white/10"
      />
    </svg>
  );
}
