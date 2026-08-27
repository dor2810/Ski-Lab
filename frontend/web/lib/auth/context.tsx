"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import {
  type AuthUser,
  loginAccount,
  registerAccount,
  refreshAccessToken,
  logoutAccount,
  googleLoginUrl,
  getCurrentUser,
  ApiError,
} from "@/lib/api";

const REFRESH_TOKEN_KEY = "ski-lab-refresh-token";

// Access tokens are short-lived (backend default: 15 min, see
// ACCESS_TOKEN_EXPIRE_MINUTES in .env.example) -- refresh a couple of
// minutes early so a search never races an about-to-expire token. If
// the backend's real expiry is shorter than this for some deployment,
// the worst case is one extra 401-triggered refresh, not a security
// problem.
const SILENT_REFRESH_MS = 13 * 60 * 1000;

interface AuthContextValue {
  user: AuthUser | null;
  accessToken: string | null;
  isLoading: boolean;
  // Set when Google's OAuth callback redirected back with an error (see
  // api/routes/google_oauth.py -- most commonly the user clicked
  // "Cancel" on Google's consent screen). Cleared by dismissGoogleError.
  googleAuthError: boolean;
  dismissGoogleError: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  loginWithGoogle: () => void;
  /**
   * Runs an authenticated API call, recovering from an expired access
   * token instead of surfacing "Not authenticated" to someone the UI
   * still shows as signed in.
   *
   * THE BUG THIS FIXES: access tokens last 15 minutes and a silent
   * refresh was scheduled at 13. A setTimeout is not a reliable clock --
   * a backgrounded tab or a slept laptop skips it -- and any single
   * refresh failure cleared the timer without rescheduling. After that,
   * every call 401'd forever while the header still said "Sign out".
   * The code even carried a comment claiming "the worst case is one
   * extra 401-triggered refresh", describing a mechanism that had never
   * actually been built. This is it.
   *
   * On 401: refresh once, retry once. If the refresh also fails the
   * session is genuinely gone (expired, revoked, or the account no
   * longer exists), so clear it and throw SessionExpiredError, which
   * callers render as "please sign in again" rather than a raw error.
   */
  runAuthed: <T,>(call: (token: string) => Promise<T>) => Promise<T>;
}

/** Thrown when a session could not be recovered and the user must sign in again. */
export class SessionExpiredError extends Error {
  constructor() {
    super("session expired");
    this.name = "SessionExpiredError";
  }
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [googleAuthError, setGoogleAuthError] = useState(false);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // runAuthed is a stable useCallback, so reading accessToken from state
  // there would capture whatever it was on first render. A ref always
  // reads the live value.
  const accessTokenRef = useRef<string | null>(null);

  const scheduleSilentRefresh = useCallback((refreshToken: string) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(async () => {
      try {
        const result = await refreshAccessToken(refreshToken);
        applySession(result.user, result.access_token, result.refresh_token);
      } catch (err) {
        // Same rule again. A transient failure here is recoverable:
        // runAuthed will refresh on the next 401, so there is no reason
        // to destroy a session the server never rejected.
        const rejected = err instanceof ApiError && (err.status === 401 || err.status === 403);
        if (rejected) clearSession();
      }
    }, SILENT_REFRESH_MS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applySession(nextUser: AuthUser, nextAccessToken: string, nextRefreshToken: string) {
    setUser(nextUser);
    setAccessToken(nextAccessToken);
    accessTokenRef.current = nextAccessToken;
    localStorage.setItem(REFRESH_TOKEN_KEY, nextRefreshToken);
    scheduleSilentRefresh(nextRefreshToken);
  }

  const runAuthed = useCallback(async function runAuthed<T>(
    call: (token: string) => Promise<T>,
  ): Promise<T> {
    const current = accessTokenRef.current;
    if (current) {
      try {
        return await call(current);
      } catch (err) {
        if (!(err instanceof ApiError) || err.status !== 401) throw err;
        // fall through to the refresh-and-retry path
      }
    }

    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    if (!storedRefreshToken) {
      clearSession();
      throw new SessionExpiredError();
    }
    try {
      const result = await refreshAccessToken(storedRefreshToken);
      applySession(result.user, result.access_token, result.refresh_token);
      return await call(result.access_token);
    } catch (err) {
      // ONLY a real rejection means the session is gone. A network
      // failure means the backend was unreachable for a moment -- a
      // Cloud Run cold start, a flaky connection, a restart -- and
      // signing the user out for that is both wrong and infuriating,
      // because their credentials were never actually refused. An
      // earlier version of this cleared on every error and logged
      // people out whenever the API hiccupped.
      const rejected = err instanceof ApiError && (err.status === 401 || err.status === 403);
      if (rejected) {
        clearSession();
        throw new SessionExpiredError();
      }
      throw err;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function clearSession() {
    setUser(null);
    setAccessToken(null);
    accessTokenRef.current = null;
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
  }

  // Runs once on mount: either pick up tokens Google's OAuth callback
  // just appended to the URL fragment (see api/routes/google_oauth.py
  // -- a fragment is never sent to any server, so this is the only
  // place they exist), or silently resume a session from a
  // previously-stored refresh token. Exactly one of these applies.
  useEffect(() => {
    (async () => {
      const hash = window.location.hash;
      if (hash.includes("access_token=")) {
        const params = new URLSearchParams(hash.replace(/^#/, ""));
        const fragmentAccessToken = params.get("access_token");
        const fragmentRefreshToken = params.get("refresh_token");
        history.replaceState(null, "", window.location.pathname + window.location.search);
        if (fragmentAccessToken && fragmentRefreshToken) {
          try {
            const meUser = await getCurrentUser(fragmentAccessToken);
            applySession(meUser, fragmentAccessToken, fragmentRefreshToken);
            setIsLoading(false);
            return;
          } catch {
            /* fall through to the stored-refresh-token path below */
          }
        }
      } else if (hash.includes("auth_error=")) {
        history.replaceState(null, "", window.location.pathname + window.location.search);
        setGoogleAuthError(true);
      }

      const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (storedRefreshToken) {
        try {
          const result = await refreshAccessToken(storedRefreshToken);
          applySession(result.user, result.access_token, result.refresh_token);
        } catch (err) {
          // Same rule as runAuthed: only DISCARD the stored token when
          // the server actually rejected it. Cloud Run scales to zero,
          // so a first page load routinely races a cold start -- and
          // throwing the refresh token away on that timeout signed
          // people out purely for arriving first.
          const rejected = err instanceof ApiError && (err.status === 401 || err.status === 403);
          if (rejected) localStorage.removeItem(REFRESH_TOKEN_KEY);
        }
      }
      setIsLoading(false);
    })();
    return () => {
      if (refreshTimer.current) clearTimeout(refreshTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function login(email: string, password: string) {
    const result = await loginAccount(email, password);
    applySession(result.user, result.access_token, result.refresh_token);
  }

  async function register(email: string, password: string, displayName?: string) {
    const result = await registerAccount(email, password, displayName);
    applySession(result.user, result.access_token, result.refresh_token);
  }

  function logout() {
    const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
    clearSession();
    if (storedRefreshToken) {
      // Best-effort revoke -- the client-side session is already gone
      // either way, so a failure here (network blip, already-expired
      // token) isn't worth surfacing to the user.
      logoutAccount(storedRefreshToken).catch(() => {});
    }
  }

  function loginWithGoogle() {
    setGoogleAuthError(false);
    window.location.href = googleLoginUrl();
  }

  function dismissGoogleError() {
    setGoogleAuthError(false);
  }

  return (
    <AuthContext.Provider
      value={{
        user, accessToken, isLoading, googleAuthError, dismissGoogleError, runAuthed,
        login, register, logout, loginWithGoogle,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
