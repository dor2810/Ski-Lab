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
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => void;
  loginWithGoogle: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scheduleSilentRefresh = useCallback((refreshToken: string) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(async () => {
      try {
        const result = await refreshAccessToken(refreshToken);
        applySession(result.user, result.access_token, result.refresh_token);
      } catch {
        clearSession();
      }
    }, SILENT_REFRESH_MS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applySession(nextUser: AuthUser, nextAccessToken: string, nextRefreshToken: string) {
    setUser(nextUser);
    setAccessToken(nextAccessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, nextRefreshToken);
    scheduleSilentRefresh(nextRefreshToken);
  }

  function clearSession() {
    setUser(null);
    setAccessToken(null);
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
      }

      const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (storedRefreshToken) {
        try {
          const result = await refreshAccessToken(storedRefreshToken);
          applySession(result.user, result.access_token, result.refresh_token);
        } catch {
          localStorage.removeItem(REFRESH_TOKEN_KEY);
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
    window.location.href = googleLoginUrl();
  }

  return (
    <AuthContext.Provider value={{ user, accessToken, isLoading, login, register, logout, loginWithGoogle }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
