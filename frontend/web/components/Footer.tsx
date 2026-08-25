"use client";

import { Logo } from "./Logo";
import { useTranslation } from "@/lib/i18n/context";

export function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="border-t border-white/10 py-10">
      <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-4 px-6 sm:flex-row">
        <div className="flex items-center gap-2.5">
          <Logo size={28} />
          <div>
            {/* Brand name deliberately never translated -- see t()'s
                dictionary keys: there is no key for "SKI LAB" itself. */}
            <span className="block text-sm font-bold tracking-wide">
              SKI <span className="text-sky">LAB</span>
            </span>
            <span className="block text-[10px] font-semibold tracking-widest text-ice/40">
              {t("footerTagline")}
            </span>
          </div>
        </div>
        <p className="text-xs text-ice/40">
          {t("footerCopyright", { year: new Date().getFullYear() })}
        </p>
      </div>
    </footer>
  );
}
