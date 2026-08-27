"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/context";
import { ApiError } from "@/lib/api";
import { useTranslation } from "@/lib/i18n/context";

// A dedicated page, not the inline dropdown ResultCard-style widgets
// use elsewhere -- the dropdown (see git history, components/
// AuthWidget.tsx) was absolutely-positioned off a corner button, which
// overflowed the viewport on narrow phone screens. A full page has no
// such constraint and is the more standard mobile pattern anyway.
export default function SignInPage() {
  const { user, isLoading, googleAuthError, login, register, loginWithGoogle } = useAuth();
  const { t } = useTranslation();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Already signed in (or just finished signing in) -- nothing left to
  // do on this page, so return to the app rather than showing a form.
  useEffect(() => {
    if (!isLoading && user) router.replace("/");
  }, [isLoading, user, router]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (mode === "register" && password.length < 12) {
      setError(t("authPasswordTooShort"));
      return;
    }
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(email, password);
      }
      router.replace("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("authErrorGeneric"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-full flex-1 items-center justify-center px-4 py-10 sm:py-16">
      <div className="w-full max-w-sm">
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-xl">
          <h1 className="mb-5 text-center text-xl font-bold text-ink">
            {mode === "login" ? t("signIn") : t("createAccount")}
          </h1>

          {googleAuthError && (
            <p className="mb-4 rounded-lg bg-warn-soft px-3 py-2 text-xs text-warn">
              {t("googleSignInFailed")}
            </p>
          )}

          <button
            type="button"
            onClick={loginWithGoogle}
            className="w-full rounded-lg border border-line py-2.5 text-sm font-semibold text-ink hover:border-line-strong"
          >
            {t("continueWithGoogle")}
          </button>

          <div className="my-4 flex items-center gap-2 text-[11px] text-subtle">
            <div className="h-px flex-1 bg-sunken" />
            {t("orDivider")}
            <div className="h-px flex-1 bg-sunken" />
          </div>

          <form onSubmit={submit} className="space-y-3">
            <input
              type="email"
              required
              placeholder={t("emailLabel")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm text-ink outline-none focus:border-sky focus:ring-1 focus:ring-sky"
            />
            <input
              type="password"
              required
              placeholder={t("passwordLabel")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-line bg-canvas px-3 py-2.5 text-sm text-ink outline-none focus:border-sky focus:ring-1 focus:ring-sky"
            />

            {error && <p className="text-xs text-warn">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-signal py-2.5 text-sm font-semibold text-ink hover:bg-signal/90 disabled:opacity-60"
            >
              {submitting ? t("authWorking") : mode === "login" ? t("signIn") : t("createAccount")}
            </button>
          </form>

          <button
            type="button"
            onClick={() => {
              setMode((m) => (m === "login" ? "register" : "login"));
              setError(null);
            }}
            className="mt-4 block w-full text-center text-xs font-medium text-sky hover:text-sky/80"
          >
            {mode === "login" ? t("authSwitchToRegister") : t("authSwitchToLogin")}
          </button>
        </div>

        <Link
          href="/"
          className="mt-6 block text-center text-xs font-medium text-subtle hover:text-muted"
        >
          {t("backToHome")}
        </Link>
      </div>
    </main>
  );
}
