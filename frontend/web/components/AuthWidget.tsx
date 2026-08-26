"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/context";
import { useTranslation } from "@/lib/i18n/context";

// Header-corner widget: signed-out state is just a link to the
// dedicated /sign-in page (see that page's own comment for why it's a
// full page now, not an inline dropdown -- the dropdown overflowed the
// viewport on narrow phone screens).
export function AuthWidget() {
  const { user, isLoading, googleAuthError, logout } = useAuth();
  const { t } = useTranslation();
  const router = useRouter();
  const pathname = usePathname();

  // A user bounced back from a canceled/failed Google sign-in should
  // immediately see why, wherever they land -- Google's own redirect
  // always returns to "/" (see api/routes/google_oauth.py's
  // FRONTEND_URL), so this fires from there and forwards to the page
  // that can actually show the error and offer a retry.
  useEffect(() => {
    if (googleAuthError && pathname !== "/sign-in") router.push("/sign-in");
  }, [googleAuthError, pathname, router]);

  if (isLoading) return null;

  if (user) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="hidden text-subtle sm:inline">{user.display_name || user.email}</span>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg border border-line px-2.5 py-1.5 font-semibold text-muted hover:border-line-strong hover:text-ink"
        >
          {t("signOut")}
        </button>
      </div>
    );
  }

  return (
    <Link
      href="/sign-in"
      className="rounded-lg bg-signal px-3 py-1.5 text-xs font-semibold text-ink hover:bg-signal/90"
    >
      {t("signIn")}
    </Link>
  );
}
