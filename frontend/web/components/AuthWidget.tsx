"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth/context";
import { ApiError } from "@/lib/api";
import { useTranslation } from "@/lib/i18n/context";

export function AuthWidget() {
  const { user, isLoading, login, register, logout, loginWithGoogle } = useAuth();
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (isLoading) return null;

  if (user) {
    return (
      <div className="flex items-center gap-2 text-xs">
        <span className="hidden text-ice/60 sm:inline">{user.display_name || user.email}</span>
        <button
          type="button"
          onClick={logout}
          className="rounded-lg border border-white/15 px-2.5 py-1.5 font-semibold text-ice/70 hover:border-white/30 hover:text-white"
        >
          {t("signOut")}
        </button>
      </div>
    );
  }

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
      setOpen(false);
      setEmail("");
      setPassword("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : t("authErrorGeneric"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="rounded-lg bg-signal px-3 py-1.5 text-xs font-semibold text-white hover:bg-signal/90"
      >
        {t("signIn")}
      </button>

      {open && (
        <div className="absolute end-0 top-full z-50 mt-2 w-72 rounded-xl border border-white/10 bg-midnight p-4 shadow-xl">
          <button
            type="button"
            onClick={loginWithGoogle}
            className="w-full rounded-lg border border-white/15 py-2 text-sm font-semibold text-white hover:border-white/30"
          >
            {t("continueWithGoogle")}
          </button>

          <div className="my-3 flex items-center gap-2 text-[11px] text-ice/40">
            <div className="h-px flex-1 bg-white/10" />
            {t("orDivider")}
            <div className="h-px flex-1 bg-white/10" />
          </div>

          <form onSubmit={submit} className="space-y-2">
            <input
              type="email"
              required
              placeholder={t("emailLabel")}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-white/15 bg-navy px-3 py-2 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky"
            />
            <input
              type="password"
              required
              placeholder={t("passwordLabel")}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-white/15 bg-navy px-3 py-2 text-sm text-white outline-none focus:border-sky focus:ring-1 focus:ring-sky"
            />

            {error && <p className="text-xs text-amber-300/90">{error}</p>}

            <button
              type="submit"
              disabled={submitting}
              className="w-full rounded-lg bg-signal py-2 text-sm font-semibold text-white hover:bg-signal/90 disabled:opacity-60"
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
            className="mt-3 text-xs font-medium text-sky hover:text-sky/80"
          >
            {mode === "login" ? t("authSwitchToRegister") : t("authSwitchToLogin")}
          </button>
        </div>
      )}
    </div>
  );
}
