import Link from "next/link";
import { Logo, Wordmark } from "./Logo";
import { AuthWidget } from "./AuthWidget";
import { LanguageSwitcher } from "./LanguageSwitcher";

// Persistent, full-width header -- always visible while scrolling, on
// every page, brand on one side and account/language controls on the
// other. Previously the logo lived inside Hero (scrolled away with the
// rest of the page) and only a small unstyled AuthWidget+
// LanguageSwitcher cluster stayed fixed in the corner -- this replaces
// both with one real navbar, matching the always-visible-header
// pattern common to ski travel sites in this market (e.g.
// skideal.co.il).
//
// HEADER_HEIGHT_PX below must match the spacer in app/layout.tsx that
// keeps page content from starting underneath this fixed bar -- kept
// as one named constant, imported by both, rather than two places
// that have to agree on a magic number.
export const HEADER_HEIGHT_PX = 64;

export function Header() {
  return (
    <header
      className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-midnight/90 backdrop-blur-sm"
      style={{ height: HEADER_HEIGHT_PX }}
    >
      <div className="mx-auto flex h-full max-w-6xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="flex items-center gap-2">
          <Logo size={32} />
          <Wordmark className="text-base" />
        </Link>

        <div className="flex items-center gap-3">
          <AuthWidget />
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}
