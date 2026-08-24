/**
 * Client for the real Ski Lab FastAPI backend (ski_optimizer/api/).
 *
 * SESSION STRATEGY: the backend's search endpoints require an
 * authenticated cookie session (see api/routes/auth.py), but this
 * landing page deliberately shows no login/account UI at all (brand
 * spec section 8: "No user accounts, login, or dashboard in this
 * pass"). ensureSession() reconciles the two: on first load it checks
 * for an existing session, and if there isn't one, silently registers
 * a disposable guest account behind the scenes -- no UI, no visible
 * step. The browser holds the resulting httpOnly session cookie itself
 * (SameSite=None; Secure, see auth.py -- required because the frontend
 * and API live on different Render subdomains); nothing is ever put in
 * localStorage/sessionStorage, per the brand spec's explicit "hold
 * state in React" requirement.
 */

const PROD_API_BASE = "https://ski-lab-api.onrender.com";

function apiBase(): string {
  if (typeof window === "undefined") return PROD_API_BASE; // build-time SSG pass, never actually fetched
  const { hostname } = window.location;
  return hostname === "localhost" || hostname === "127.0.0.1"
    ? "http://localhost:8000"
    : PROD_API_BASE;
}

const CSRF_HEADER = "X-Requested-With";
const CSRF_VALUE = "SkiLab";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function apiFetch<T>(
  path: string,
  init: { method?: string; body?: unknown } = {}
): Promise<T> {
  const { method = "GET", body } = init;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (method !== "GET") headers[CSRF_HEADER] = CSRF_VALUE;

  const resp = await fetch(apiBase() + path, {
    method,
    credentials: "include",
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  let data: unknown = null;
  try {
    data = await resp.json();
  } catch {
    /* no/invalid JSON body */
  }
  if (!resp.ok) {
    const detail =
      (data && typeof data === "object" && "detail" in data
        ? (data as { detail: unknown }).detail
        : null) ?? resp.statusText;
    throw new ApiError(resp.status, typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data as T;
}

function randomGuestCredentials(): { email: string; password: string } {
  const id =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  // example.com is reserved for documentation but IS accepted by the
  // backend's email validator (checked directly against a running
  // instance -- it only rejects special-use TLDs like .test/.invalid,
  // not multi-label domains under a normal TLD).
  return {
    email: `guest-${id}@example.com`,
    password: `sl-${id}-${id}`, // well over the 12-char minimum, never shown to anyone
  };
}

let sessionPromise: Promise<void> | null = null;

/** Idempotent -- safe to call from multiple components; only does the network round-trip once. */
export function ensureSession(): Promise<void> {
  if (!sessionPromise) {
    sessionPromise = (async () => {
      try {
        await apiFetch("/auth/me");
        return; // existing cookie session is still valid
      } catch {
        // fall through to registration
      }
      const creds = randomGuestCredentials();
      await apiFetch("/auth/register", { method: "POST", body: creds });
    })();
  }
  return sessionPromise;
}

// --- Shared response shapes (mirrors ski_optimizer/api/routes/search.py) ---

export interface TerrainMix {
  beginner: number;
  intermediate: number;
  advanced: number;
  quality: "sourced" | "sourced_conflicting" | "estimated";
}

export interface Resort {
  name: string;
  country: string;
  region: string;
  piste_km: number;
  off_piste_rating: number;
  snow_reliability: number;
  nightlife_rating: number;
  family_friendliness: number;
  nearest_airport: string;
  transfer_time_minutes: number;
  terrain: TerrainMix | null;
  needs_verification: boolean;
}

export interface CostBreakdown {
  flight_eur: number;
  transfer_eur: number;
  accommodation_eur: number;
  ski_pass_eur: number;
  equipment_eur: number;
  food_eur: number;
  misc_eur: number;
  total_eur: number;
  flight_price_is_live: boolean;
  accommodation_price_is_live: boolean;
}

export interface TripResult {
  resort: Resort;
  cost: CostBreakdown;
  score: number;
  score_components: Record<string, number>;
  explanation: string;
  within_budget: boolean;
  // Only present on /trips/search-dates results.
  start_date?: string;
  end_date?: string;
  season?: "peak" | "high" | "shoulder";
}

export interface SearchResponse {
  query_resort_count: number;
  live_pricing_active: boolean;
  results: TripResult[];
}

export interface SearchDateRangeResponse extends SearchResponse {
  candidate_dates_per_resort: number;
}

export type SkillLevel = "beginner" | "intermediate" | "advanced" | "expert";
export type AccommodationTier = "budget" | "standard" | "luxury";
export type FoodProfile = "budget" | "normal" | "luxury";
export type EquipmentTier = "standard" | "premium";
export type TransferMode = "shared_shuttle" | "private_transfer" | "train" | "bus";

export interface Weights {
  ski_quality: number;
  price: number;
  snow: number;
  nightlife: number;
  convenience: number;
  accommodation: number;
}

export interface CommonSearchFields {
  budget_eur_per_person: number;
  min_budget_eur_per_person?: number | null;
  group_size: number;
  skill_level: SkillLevel;
  accommodation_tier: AccommodationTier;
  food_profile: FoodProfile;
  equipment_tier: EquipmentTier;
  target_resort?: string | null;
  max_connections?: number | null; // 0 nonstop / 1 / 2 / null = no preference
  preferred_transfer_modes?: TransferMode[] | null;
  weights: Weights;
}

export interface FixedDateSearchParams extends CommonSearchFields {
  trip_nights: number;
  // Optional: omitting it skips season-band adjustment AND live
  // flight/accommodation repricing (see api/routes/search.py), giving a
  // fast, quota-free, static-estimate result. Used for the landing
  // page's auto-populated initial view; the actual search form always
  // supplies a real date, which is what triggers live pricing.
  outbound_date?: string; // YYYY-MM-DD
  top_n?: number;
}

export interface FlexibleWindowSearchParams extends CommonSearchFields {
  trip_nights: number;
  earliest_date: string;
  latest_date: string;
  top_n?: number;
}

export async function searchFixedDates(params: FixedDateSearchParams): Promise<SearchResponse> {
  await ensureSession();
  return apiFetch<SearchResponse>("/trips/search", { method: "POST", body: params });
}

export async function searchFlexibleWindow(
  params: FlexibleWindowSearchParams
): Promise<SearchDateRangeResponse> {
  await ensureSession();
  return apiFetch<SearchDateRangeResponse>("/trips/search-dates", { method: "POST", body: params });
}

export async function listResortNames(): Promise<string[]> {
  await ensureSession();
  return apiFetch<string[]>("/trips/resorts");
}
