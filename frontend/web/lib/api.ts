/**
 * Client for the real Ski Lab FastAPI backend (ski_optimizer/api/).
 *
 * AUTH STRATEGY: bearer token, not cookies. Search
 * (/trips/search, /trips/search-dates, /trips/resorts) requires a
 * signed-in user (see api/routes/auth.get_current_user_for_search) --
 * every authenticated call here takes an explicit accessToken and
 * sends it as `Authorization: Bearer <token>`. This project already
 * tried cookie-based sessions and hit a structural wall: the frontend
 * (Firebase Hosting, web.app) and API (Cloud Run, run.app) live on
 * different domains, both on the Public Suffix List, so they're
 * different SITES to a browser, and a growing number of browsers
 * block or restrict third-party (cross-site) cookies by default
 * regardless of SameSite. A bearer token the client attaches
 * explicitly sidesteps that whole failure class. See
 * lib/auth/context.tsx for where accessToken actually comes from and
 * how it's kept fresh.
 */

// Cloud Run's default URL (see Dockerfile + the ski-lab-api Cloud Run
// service, region us-central1 -- chosen because it's one of Cloud
// Run's always-free-tier regions). Backend was previously on Render;
// migrated off it entirely, see git history for that cutover.
const PROD_API_BASE = "https://ski-lab-api-449641203618.us-central1.run.app";

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
  init: { method?: string; body?: unknown; accessToken?: string | null } = {}
): Promise<T> {
  const { method = "GET", body, accessToken } = init;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (method !== "GET") headers[CSRF_HEADER] = CSRF_VALUE;
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

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
  // True = ski_pass_eur is a REAL published 6-day price researched from
  // the resort's own ticketing pages, not the seed estimate. Not
  // per-request "live" like the two above, but sourced rather than
  // guessed -- see api/routes/search.py's CostBreakdownOut.
  ski_pass_price_is_researched: boolean;
}

// ONE day of a trip's weather. is_live_forecast true = a real forecast
// (only possible within ~15 days out; description set, years_sampled
// null) -- false = a historical average for that SAME calendar day
// across several past years (description null, years_sampled set).
// See adapters/weather_adapter.get_trip_weather's docstring on the
// backend for why a trip's days can be a genuine mix of both.
export interface DailyWeather {
  date: string; // YYYY-MM-DD
  is_live_forecast: boolean;
  temp_max_c: number;
  temp_min_c: number;
  snowfall_cm: number;
  // Actual ground/base snow depth, NOT recent snowfall (see
  // snowfall_cm above) -- the real "is there snow to ski on" answer.
  snow_depth_cm: number;
  description: string | null;
  years_sampled: number | null;
}

// A whole trip's weather: one DailyWeather per day from check-in to
// check-out inclusive, plus an overall average. days can be shorter
// than the full trip length if some days genuinely have no data.
export interface TripWeather {
  days: DailyWeather[];
  avg_temp_max_c: number;
  avg_temp_min_c: number;
  avg_snowfall_cm: number;
  avg_snow_depth_cm: number;
}

/** One real itinerary behind a result's flight price, cheapest first. */
export interface FlightOption {
  price_eur: number;
  airline: string;
  duration_minutes: number;
  stops: number;
  is_cheapest: boolean;
  /**
   * The curated labels this itinerary won: "cheapest" / "best" /
   * "fastest" -- the triad every flight product uses (Skyscanner's
   * default sort is literally "Best"). One flight can hold several and
   * is then shown once with all of them.
   */
  roles: string[];
  /** Real designators per leg, e.g. ["LX 253", "LX 2802"]. Empty when unknown. */
  flight_numbers: string[];
  /** What the WHOLE trip costs if this flight is the one taken. */
  trip_total_eur: number;
}

/**
 * One real, named property behind a result's accommodation price,
 * cheapest first. No "best" pick, deliberately: the provider's
 * rating/distance fields aren't parsed, so price is the only honest
 * axis to rank on.
 */
export interface AccommodationOption {
  property_name: string;
  price_eur_per_night: number;
  /** What this property costs this traveller for the whole stay. */
  per_person_eur: number;
  is_cheapest: boolean;
  /** The whole trip's cost if this property is the one booked. */
  trip_total_eur: number;
  /**
   * Dated Google Hotels link narrowed to this property (results page
   * with the property surfaced on top -- not a guaranteed
   * single-property landing page).
   */
  url: string;
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
  // Deep links to Google's own live search results. For the single
  // top-ranked result, these usually land directly on the specific
  // priced flight/hotel when a live quote could be matched to a real
  // bookable page; every other result (and any case where that match
  // failed) gets Google's plain search results instead -- see
  // api/routes/search.py's _flight_search_url/_accommodation_search_url
  // on the backend for the exact fallback contract.
  // flight_search_url is null when the resort's airport field has no
  // parseable IATA code.
  flight_search_url: string | null;
  accommodation_search_url: string;
  // The real name of the cheapest live-priced property this result's
  // accommodation_eur is FOR (e.g. "Hôtel Le Dahu") -- populated for
  // every live-priced result, not just the top one. null when
  // accommodation pricing isn't live for this result (no outbound
  // date, or the live lookup failed -- same cases where cost.
  // accommodation_price_is_live is false).
  accommodation_property_name: string | null;
  // The real itineraries behind flight_eur, cheapest first. Empty when
  // the flight price isn't live -- with a static estimate there are no
  // real flights to list.
  flight_options: FlightOption[];
  // The real named properties behind accommodation_eur, cheapest
  // first. Same contract: empty unless the accommodation price is live.
  accommodation_options: AccommodationOption[];
  // The trip total is a RANGE: total_eur is the low end (cheapest
  // flight) and this is the high end (typically the fastest/nonstop).
  // null when there is only one real flight choice.
  total_eur_with_fastest_flight: number | null;
  // A booking link -- always real and working, same contract as
  // flight/accommodation above: a live quote for the top result when
  // available, Alps2Alps' own booking form otherwise. See
  // api/routes/search.py's _transfer_search_url docstring on the
  // backend.
  transfer_search_url: string;
  // Real, working links for equipment rental and lift-pass purchase --
  // see engine/links.py's equipment_search_url()/ski_pass_search_url()
  // on the backend for exactly what each is (a verified rental
  // network's front door vs. a resort-named Google search) and what's
  // NOT resort-guaranteed about them. Always populated, every result.
  equipment_search_url: string;
  ski_pass_search_url: string;
  // Only ever populated for the single top-ranked result (a live
  // lookup, same reasoning as the booking links above).
  weather: TripWeather | null;
}

/** What a search cost and what's left today. null for anonymous search. */
export interface Credits {
  cost: number;
  remaining: number;
  daily_allowance: number;
}

export interface SearchResponse {
  query_resort_count: number;
  live_pricing_active: boolean;
  results: TripResult[];
  credits: Credits | null;
  // True when a live-pricing provider served an anti-bot challenge
  // during this search. Prices fell back to estimates -- the per-line
  // badges already say that; this explains WHY, so we can tell the user
  // instead of showing a wall of unexplained EST. badges.
  live_pricing_blocked: boolean;
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
  family: number;
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
  // Full days actually spent on the mountain, NOT nights away -- the
  // backend derives nights = ski_days + 1 (see
  // models.UserPreferences.nights), since you arrive the evening
  // before your first ski day and leave the day after your last one.
  ski_days: number;
  // Optional: omitting it skips season-band adjustment AND live
  // flight/accommodation repricing (see api/routes/search.py), giving a
  // fast, quota-free, static-estimate result. Used for the landing
  // page's auto-populated initial view; the actual search form always
  // supplies a real date, which is what triggers live pricing.
  outbound_date?: string; // YYYY-MM-DD
  top_n?: number;
}

export interface FlexibleWindowSearchParams extends CommonSearchFields {
  // See FixedDateSearchParams.ski_days -- same contract.
  ski_days: number;
  earliest_date: string;
  latest_date: string;
  top_n?: number;
  // Restrict candidate start dates to just this weekday (e.g. many
  // people prefer a trip that starts on a Saturday, not mid-week).
  // null/omitted = every day in the window is a candidate.
  start_weekday?: WeekdayName | null;
}

/**
 * A Google Flights booking-page deep link for ONE specific itinerary a
 * search already showed, matched by its flight numbers. Built at CLICK
 * time (each link costs the backend an extra live request, and a link
 * built now is fresher than one aged inside the search response). url
 * is null when the itinerary can no longer be matched -- the caller
 * falls back to the result's plain flight_search_url, never a broken
 * link.
 */
export async function fetchFlightBookingLink(
  params: {
    resort_name: string;
    outbound_date: string; // YYYY-MM-DD
    return_date: string; // YYYY-MM-DD
    flight_numbers: string[];
    max_connections: number | null;
  },
  accessToken: string
): Promise<{ url: string | null }> {
  return apiFetch<{ url: string | null }>("/trips/flight-booking-link", {
    method: "POST", body: params, accessToken,
  });
}

export async function searchFixedDates(
  params: FixedDateSearchParams,
  accessToken: string
): Promise<SearchResponse> {
  return apiFetch<SearchResponse>("/trips/search", { method: "POST", body: params, accessToken });
}

export async function searchFlexibleWindow(
  params: FlexibleWindowSearchParams,
  accessToken: string
): Promise<SearchDateRangeResponse> {
  return apiFetch<SearchDateRangeResponse>("/trips/search-dates", {
    method: "POST", body: params, accessToken,
  });
}

/**
 * Resort names for the picker.
 *
 * mainstreamOnly returns the curated shortlist -- resorts real
 * ski-package operators actually sell, plus a few marquee names (see
 * data/mainstream_resorts.py on the backend). Nothing is removed from
 * the database; this is the default the UI shows, and "show all"
 * fetches the full set.
 */
export async function listResortNames(
  accessToken: string,
  mainstreamOnly = false
): Promise<string[]> {
  const query = mainstreamOnly ? "?mainstream_only=true" : "";
  return apiFetch<string[]>(`/trips/resorts${query}`, { accessToken });
}

/**
 * The hand-picked "most popular" set the picker's one-tap button
 * selects. Comes from the backend rather than being duplicated here, so
 * there is one place to change the list and no way for the two to drift.
 * Returned in curated order -- the order is part of the curation.
 */
export async function listPopularResortNames(accessToken: string): Promise<string[]> {
  return apiFetch<string[]>("/trips/resorts?popular_only=true", { accessToken });
}

// --- Auth (see api/routes/auth.py + lib/auth/context.tsx) ---

export interface AuthUser {
  id: string;
  email: string;
  display_name: string | null;
  is_email_verified: boolean;
}

export interface AuthResult {
  user: AuthUser;
  access_token: string;
  refresh_token: string;
}

export async function registerAccount(
  email: string,
  password: string,
  display_name?: string
): Promise<AuthResult> {
  return apiFetch<AuthResult>("/auth/register", { method: "POST", body: { email, password, display_name } });
}

export async function loginAccount(email: string, password: string): Promise<AuthResult> {
  return apiFetch<AuthResult>("/auth/login", { method: "POST", body: { email, password } });
}

export async function getCurrentUser(accessToken: string): Promise<AuthUser> {
  return apiFetch<AuthUser>("/auth/me", { accessToken });
}

export async function refreshAccessToken(refresh_token: string): Promise<AuthResult> {
  return apiFetch<AuthResult>("/auth/refresh", { method: "POST", body: { refresh_token } });
}

export async function logoutAccount(refresh_token: string): Promise<void> {
  await apiFetch<{ message: string }>("/auth/logout", { method: "POST", body: { refresh_token } });
}

// A plain browser navigation (not a fetch), so the backend's redirect
// chain to Google and back can set no cookie and rely on nothing but
// the URL fragment it appends on return -- see google_oauth.py.
export function googleLoginUrl(): string {
  return apiBase() + "/auth/google/login";
}


/** Today's remaining search credits. Read-only -- never spends one. */
export async function getSearchCredits(accessToken: string): Promise<Credits> {
  return apiFetch<Credits>("/trips/credits", { accessToken });
}
