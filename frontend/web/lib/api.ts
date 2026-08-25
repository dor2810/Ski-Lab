/**
 * Client for the real Ski Lab FastAPI backend (ski_optimizer/api/).
 *
 * SESSION STRATEGY: none, deliberately. Search
 * (/trips/search, /trips/search-dates, /trips/resorts) is anonymous by
 * default on the backend now (see api/routes/auth.get_current_user_for_search)
 * -- no cookie, no session, no register call needed. This file used to
 * silently self-register a disposable guest account before every
 * search to work around an auth requirement; that machinery is gone
 * because the requirement itself is gone, not just hidden. It was also
 * the likely cause of real, hard-to-diagnose failures: the frontend and
 * API live on different onrender.com subdomains, and a growing number
 * of browsers block or restrict third-party (cross-site) cookies by
 * default (Safari has for years; others are moving the same way) --
 * SameSite=None doesn't help with THAT restriction, only with the
 * SameSite mechanism itself. Removing the cookie dependency for search
 * removes that whole failure class, not just papers over one symptom
 * of it. The backend's real cost control for live pricing is now
 * api/rate_limit.py, not auth.
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

export type WeekdayName =
  | "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";

export interface CommonSearchFields {
  budget_eur_per_person: number;
  min_budget_eur_per_person?: number | null;
  group_size: number;
  skill_level: SkillLevel;
  accommodation_tier: AccommodationTier;
  food_profile: FoodProfile;
  equipment_tier: EquipmentTier;
  target_resort?: string | null;
  // "Only these" -- 2-3 (or any number of) specific resorts.
  include_resorts?: string[] | null;
  // "Everywhere except these".
  exclude_resorts?: string[] | null;
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
  // Restrict candidate start dates to just this weekday (e.g. many
  // people prefer a trip that starts on a Saturday, not mid-week).
  // null/omitted = every day in the window is a candidate.
  start_weekday?: WeekdayName | null;
}

export async function searchFixedDates(params: FixedDateSearchParams): Promise<SearchResponse> {
  return apiFetch<SearchResponse>("/trips/search", { method: "POST", body: params });
}

export async function searchFlexibleWindow(
  params: FlexibleWindowSearchParams
): Promise<SearchDateRangeResponse> {
  return apiFetch<SearchDateRangeResponse>("/trips/search-dates", { method: "POST", body: params });
}

export async function listResortNames(): Promise<string[]> {
  return apiFetch<string[]>("/trips/resorts");
}
