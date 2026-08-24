# Ski Lab — Project State

*Updated 2026-08-24, after the first Mac session actually ran the suite. Supersedes the "initial build sessions" version of this file and any earlier handoff document. Read this first.*

---

## 1. The verification ledger — read this before trusting anything

This is the single most important section. The codebase divides sharply into code that has genuinely run and code that has not.

| Component | Tests | Status |
|---|---|---|
| Engine: cost calculator, scoring, terrain matching | ✅ | 163 tests passing |
| Validation layer | ✅ | Running |
| Flight adapter — *parsing only* | ✅ | 28 tests vs. a fixture |
| Response cache | ✅ | 12 tests running |
| Date-range search | ✅ | 22 tests running |
| Transfer engine | ✅ | 29 tests running |
| **Fare-history persistence** | ✅ | 20 tests, now running (sqlalchemy installed) — was 8 skipped |
| **Auth backend** (register/login/JWT/Google OAuth) | ✅ | **Executed for the first time.** All 20 tests pass now, after fixing 3 real bugs found by running it (see §6, items 11–13) |
| **Search API route** | ✅ | **Executed for the first time.** All 12 tests pass now, same 3 bugs as auth (shared cause) |
| **Live SerpApi requests** | ✅ | **Verified live** — real TLV→GVA,INN search returned 12 real options; multi-airport search works as documented |
| **Cost estimates vs. reality** | ⚠️ | **Partially checked** — flight leg only. Flat estimate (€280, Chamonix/GVA) landed close to a real live peak-season quote (€261–268, same route). Ski pass/transfer/food estimates still unchecked; accommodation now has a live source (see below) but the ESTIMATE-vs-REALITY gap itself hasn't been analyzed yet |
| **Live flight pricing, wired into the engine** | ✅ | `rank_trips()`, `search_date_range()`, and both `/trips/search` + `/trips/search-dates` APIs replace the static flight estimate with a real SerpApi quote |
| **Accommodation adapter (Booking.com Demand API)** | ⚠️ | Real interface + parsing written, 12 tests passing against a fixture — **still never called live**, `BOOKING_AFFILIATE_API_KEY` still doesn't exist (Managed Affiliate Partner approval still paused, per §5b). **This is no longer the active accommodation source** — see next row |
| **Accommodation via SerpApi Google Hotels (NEW)** | ✅ | **New this session, verified live.** `adapters/serpapi_hotel_adapter.py` — same interface as the Booking.com adapter, same `SERPAPI_API_KEY` as flights, no new procurement needed. 17 tests against a fixture, PLUS a real live call confirmed working (Val Thorens, Jan 2027: real per-night rate, correctly varies by date). Wired into `rank_trips()` and `search_date_range()` via `accommodation_cost_fn`, exactly like live flight pricing. `CostBreakdown.accommodation_price_is_live` tags which is which, same pattern as `flight_price_is_live`. Known limitation stated in the adapter's own docstring: SerpApi's Google Hotels has no "N rooms" param, so the adapter prices one room and the cost layer multiplies by `rooms_needed` itself; `distance_to_lifts_km` is always `None` (Google Hotels doesn't return it, and the code doesn't fabricate it) |
| **Date-range search API — `POST /trips/search-dates` (NEW)** | ✅ | **New this session.** Wraps `engine/date_search.search_date_range`. Give it an earliest/latest date window + trip length (+ optionally a specific resort) and it searches every valid start date in the window, live-priced. Verified: a 10-day window with a 7-night trip correctly yields 4 candidate start dates. 14 API tests + verified live against real Val Thorens dates |
| **Over-budget fallback (NEW)** | ✅ | **New this session, in both `rank_trips()` and `search_date_range()`.** Previously, "nothing fits the budget" returned an empty list. Now it returns the cheapest option(s) actually found instead, tagged `within_budget=False` (surfaced through the API and the explainer's "why" text) — never silently presented as a normal fitting result. Old "empty means nothing fits" behavior is still available via `allow_over_budget_fallback=False`. Covered by tests that verify the flag, not just non-emptiness |
| **Flight connections preference (NEW)** | ✅ | **New this session.** `max_connections` (0/1/2/None) exposed on both search APIs, threaded through to `live_flight_cost_eur` → `flight_adapter._stops_param` (already existed, was just never exposed above the adapter layer). SerpApi can express "at most N stops" or "any", not "at least N" — so "2+ stops OK" maps to "no preference," documented honestly in the API schema's field comment, not glossed over |
| **Budget range / floor (NEW)** | ✅ | **New this session.** `min_budget_eur_per_person` on both search APIs — simple post-filter, no engine change needed since low cost was never pruned early. Unlike the budget ceiling, no fallback-when-empty semantics: "nothing above my floor" is a real, legitimate empty result |
| **Frontend — `frontend/app/index.html` (NEW)** | ✅ | **New this session.** A self-contained, dependency-free HTML/JS page (no build tooling) that calls the real FastAPI backend — NOT the old `SkiTripOptimizer.jsx` prototype's embedded JS engine port. Real auth (register/login against `/auth/*`, httpOnly cookies, CSRF header), both search modes, connections/budget-range controls, LIVE/est. badges per cost component, visible over-budget-fallback banner. Verified end-to-end via curl against a running backend (real register → real login → real live-priced search, twice, for both endpoints) before being handed to the user — the browser click-through itself is NOT verified in this sandbox (no working Claude-in-Chrome connection this session); ask the user to confirm it actually renders/works in their browser |

**270 of 270 tests pass** as of this session (up from 224 at the start of today).

**New finding from the live call, not knowable from tests — corrected once, see below:** SerpApi's `price_insights` (lowest_price, price_level, price_history — the "is this fare actually good?" feature that was part of the reason SerpApi was chosen over a conventional API, see §5) is **not reliably present, and it's not simply about single- vs multi-airport.**

- `TLV → GVA,INN` (multi-airport): no `price_insights` key at all.
- `TLV → GVA` (single-airport, same dates): full `price_insights`.
- `TLV → GVA,CMF` (multi-airport, different dates): full `price_insights`.

The first two results led to an initial (wrong) conclusion here that multi-airport search always drops insights — the third result, from checking Val Thorens, disproves that. The real pattern looks route/date/data-availability dependent on Google's side, not something our adapter controls or can predict from the request shape alone. Confirmed against raw JSON each time, not a parsing bug in our adapter. **Practical implication: `insight` must always be treated as optional (`None`-able) regardless of query shape** — already true in the code (`Optional[PriceInsight]`), so no adapter change needed, just don't assume you can force insights by restricting to one airport.

**A second thing checked and confirmed SAFE (worth recording since it looked like a real bug at first):** SerpApi's round-trip flow returns a `departure_token` alongside the outbound-leg options, which normally means a second call is needed to fetch/select the return leg — raising the concern that `price_eur` might be an outbound-only figure our adapter was silently treating as the full round-trip cost (`_parse_flight` in `adapters/flight_adapter.py` never follows `departure_token`). Checked directly: called the API once normally (price €292), then followed that response's `departure_token` in a second, independent call to fetch the paired return leg — it reported the identical total, €292. So the price from a single, un-chained call already is the full round-trip total for that itinerary; the adapter does not need to be changed to follow `departure_token`. Confirmed via live data, not inferred.

That second-to-last row deserves emphasis: nobody has yet checked whether a Ski Lab estimate resembles what the trip actually costs. That is the question the entire product rests on, and it's still open.

---

## 2. What the product is

A **trip optimization engine**, not a recommendation chatbot, for Israeli travelers going to European ski resorts.

**Differentiator:** existing tools optimize one leg in isolation (Skyscanner: flights; Booking: hotels). ChatGPT can reason but has no grounded pricing data and will fabricate numbers. Ski Lab combines every component into a real total cost, ranked by personalized weights, with an LLM used only for language — never for generating a price or score.

**Two query modes, both built:**
- *Plan my trip* — fixed dates, rank resorts
- *Best value* — fixed budget and duration, flexible dates in a window; ranks resort × date combinations. Serves the value-seeking traveler.

**Branding:** "Ski Lab." Wordmark is "SKI" + a "LAB" pill tag; icon is a peak silhouette crossed by a survey line with an amber sample point — "the mountain, measured." Palette: Crevasse `#0B1526`, Piste Blue `#4A8FE0`, Piste Red `#D64545`, Amber Couloir `#E8A548`. The three accent colors are **functional** — they encode beginner/intermediate/advanced terrain — and must not be repurposed (never Piste Red for errors).

---

## 3. Architecture

```
ski_optimizer/
├── models.py              Resort, UserPreferences, CostBreakdown, TripOption,
│                          FlightOption, PriceInsight  + shared enum constants
├── data/
│   └── resort_repository.py    reads Resort objects from the xlsx
├── adapters/              ONE FILE PER EXTERNAL SOURCE — nothing else does I/O
│   ├── flight_adapter.py       SerpApi Google Flights (built, unverified live)
│   ├── response_cache.py       bounded LRU + TTL, swappable for Redis
│   ├── email_adapter.py        console backend works; real provider stubbed
│   └── accommodation/transfer/weather/snow_adapter.py   stubs
├── engine/                PURE LOGIC — no network, no LLM
│   ├── cost_calculator.py      all cost components + season bands
│   ├── scoring.py              hard filter + weighted multi-objective scoring
│   ├── terrain.py              structured terrain matching
│   ├── transfers.py            mode selection, availability, multi-vehicle
│   ├── date_search.py          three-stage funnel for flexible dates
│   └── reranker.py             stub (weather/snow re-ranking)
├── nlp/                   THE ONLY PLACE AN LLM IS CALLED
│   ├── explainer.py            template today; LLM version later, same interface
│   └── preference_parser.py    stub
├── db/                    SQLAlchemy — auth tables + fare history
├── api/                   FastAPI — auth + protected search route
└── cli/main.py            working demo entrypoint
```

**The load-bearing principle:** every external source is isolated behind an adapter, and `engine/` never sees a provider's response shape. Swapping SerpApi for something else touches one file.

---

## 4. Data assets

**`ski_resort_database_seed.xlsx`** — 30 resorts, 8 countries, 31 columns. Includes structured beginner/intermediate/advanced terrain percentages, snowfall, glacier access, season dates, terrain park, and **Israeli flight access** (audience-specific: e.g. Innsbruck has direct Israir service; Bansko/Sofia has dedicated Israeli charter packages).

**`transfer_options.xlsx`** — 56 transfer options covering **26 of 46** airport–resort pairs (GVA, INN, CMF, GNB, LYS). One row per (airport, resort, mode) with `cost_basis` (per_person vs per_vehicle), duration, availability by day, and mandatory flags.

Every field carries a quality tag: `sourced`, `sourced_conflicting`, or `estimated`.

---

## 5. Key decisions and why

**Flights: SerpApi now, add Duffel later.** Amadeus Self-Service shut down July 2026 and Kiwi went invite-only, so the obvious defaults are gone. SerpApi is a *scraper* — chosen anyway because it does two things a conventional API can't: multi-airport search in one request (`arrival_id=GVA,INN`), and price history/insights (is this fare actually good?). It cannot issue tickets, so Duffel gets **added, not swapped in**, for booking. Ignav was evaluated and **dropped as unverifiable** — no independent source, undisclosed data provenance.

**Transfers: curated table, not an API.** Only 46 fixed pairs, prices change seasonally, and there are barely any APIs anyway. This is a lookup table refreshed twice a season.

**Cost tiers for date-range search:**
- *Varies continuously*: flight, accommodation ← the search axes
- *Varies by season band*: ski pass, accommodation
- *Date-independent per resort*: transfer, equipment, food

Tier 3 costs cancel out when comparing dates for one resort — which is what makes a month-wide search tractable. **Not** because they're small or uniform: researched transfers range €22 to €220.

**Persist fare history.** Every search records what it saw. After a season, "which week is cheapest to Innsbruck?" is answerable from our own data — an asset that survives SerpApi changing or disappearing.

**5a. Live flight pricing: static-first, reprice-top-N, never drop a resort over an API hiccup.** With a 250 SerpApi calls/month budget, live-pricing all 30 resorts on every search was a non-starter (12% of monthly quota, one request). The design landed on: rank with the static estimate first (free), then live-price only the top `live_reprice_n` candidates (default 10 — more than the returned `top_n` so a resort whose live price undercuts its static estimate can still surface), re-sort, return. `UserPreferences.outbound_date` and `rank_trips(..., flight_cost_fn=...)` are both new and both optional — omitting them reproduces the exact previous behavior, verified by 212 pre-existing tests staying green untouched. A resort the live call can't price (`None` — adapter error, no route) keeps its static estimate rather than being dropped; a resort whose *real* price busts the budget IS dropped, same hard-constraint rule as everywhere else. `cost_calculator.apply_live_flight_price()` is the one place the "swap in a live price" arithmetic lives, shared by both `rank_trips()` and `date_search.search_date_range()` (which had its own copy of this logic before today — consolidated, not duplicated further). `CostBreakdown.flight_price_is_live` tags which is which, surfaced through the API (`CostBreakdownOut.flight_price_is_live`) and the explainer's "why" text.

A genuine bonus found while wiring this: `rank_trips()` was never passing `start_date` into `compute_trip_cost()`, even though season-band adjustment (ski pass, accommodation) already existed and needed exactly that. It was dead code until today. Now that it fires, a real gap surfaced immediately: Val Thorens on Jan 2, 2027 (New Year peak) prices out at €1,657 against a €1,500 budget using ONLY the static/season-adjusted estimate, before any live flight pricing is even involved — worth knowing before assuming every "over budget" result is about flights.

**5b. Accommodation: real interface built, live call blocked on a provider key — and that's likely to stay true for a while.** `adapters/accommodation_adapter.py` now has a genuine implementation (request building, `AdapterError` handling, response parsing) targeting Booking.com's Demand API, with 12 tests passing against a hand-built fixture — same shape `flight_adapter.py` had before its first real key. It is gated behind `BOOKING_AFFILIATE_API_KEY` and raises a clear, specific error when that's unset, which today is always. **Checked directly (2026-08-24) rather than assumed:** Booking.com's basic Affiliate Partner signup does NOT itself grant API access. Real API/Demand API access requires a separate "Managed Affiliate Partner" approval track — Partner Centre access, then presenting the actual integration project for review — and that track is **currently paused for new applicants** industry-wide (a Terms and Conditions update), not just slow. So finishing the in-progress basic affiliate signup will not, by itself, produce a working key. If live accommodation data matters sooner, Expedia Rapid is worth checking as an alternative — not evaluated yet. The fixture's field names (`block`, `price.amount`, `review_score`, etc.) are a best-effort approximation from Booking's published docs, not verified against a real response — expect adjustment on the first real call, exactly as SerpApi's fixture needed adjustment after its first live call this session.

---

## 6. Bugs found and fixed — the pattern is instructive

These were all found by checking rather than assuming. Expect more of the same class.

1. **Negative `trip_nights` produced negative costs** that passed the budget filter and were returned as valid results. Root cause: validation lived only at the API boundary.
2. **Transfer times were averaged across different airports.** Val Thorens' "3h GVA / 1h45 CMF" became 127.5 minutes — a number describing no real journey. Worse, the flight adapter searches both airports, so the two halves of one trip disagreed.
3. **Minutes-only transfer strings silently fell back to a 120-minute default.** Krvavec's "~20min" was scored as a 2-hour transfer — a 6× error on the resort whose entire selling point is proximity.
4. **Off-piste was weighted flat regardless of skill**, floating expert resorts to the top of a *beginner's* list, and rewarding resorts with *missing* terrain data.
5. **Ski pass was flat-linear and stored the shoulder-season price.** Peak trips understated ~18%.
6. **The transfer engine was built but never wired in** — all that research wasn't reaching actual costs. Zermatt was understated by half (€107 vs €220).
7. **Email was case-sensitive throughout auth** — `Dor@x.com` and `dor@x.com` would create two accounts.
8. **A regex script silently failed to write** while a shallow check made it look successful.
9. **A test with a 500m tolerance could never fail** (real max deviation: 10m).
10. **Eight tests reported PASS while executing nothing** (silent skip when sqlalchemy was absent).
11. **CSRF middleware raised `HTTPException` instead of returning a response.** `enforce_csrf_header` in `api/main.py` sits in an `@app.middleware("http")` function, which is outside the reach of Starlette's `ExceptionMiddleware` (that only wraps the router/endpoints). Raising there propagated as an unhandled exception instead of becoming a 403 — crashed the request instead of rejecting it. Fixed by returning a `JSONResponse(403, ...)` directly.
12. **`test_auth.py` and `test_search.py` silently clobbered each other's DB.** Both files independently did `app.dependency_overrides[get_db] = override_get_db` at *module import time*, on the same shared FastAPI `app` singleton. Since pytest imports every test module before running any test, whichever file was imported last (`test_search.py`, alphabetically) won the override for the **entire session** — so every `test_auth.py` request silently ran against `test_search.py`'s engine, which had no tables from `test_auth.py`'s perspective (`no such table: users`). Confirmed by running `test_auth.py` alone: only 3 of 13 failures, not 13. Fixed by moving the override into the `_fresh_db` fixture's setup/teardown instead of module scope.
13. **`secure=True` cookies never reached `TestClient` on a second request.** `routes/auth.py` sets auth cookies with `secure=True` (correct for production HTTPS). `TestClient`'s default `base_url="http://testserver"` means httpx's cookie jar stores the cookie but won't attach it to later requests — a real browser grants `localhost` an exception, `TestClient` doesn't. Every "authenticated" follow-up call in the test suite got 401. Fixed by instantiating `TestClient(app, base_url="https://testserver")` everywhere in the tests; the production `secure=True` cookie setting itself is correct and was left unchanged.

---

## 7. Known gaps — documented, not bugs to re-report

- **Transfer airport consistency.** With no airport specified, transfer resolves to the cheapest airport for that resort (Val Thorens → Lyon €85, not Geneva €100). Fixing it needs the flight search to report its chosen airport.
- **20 of 46 transfer pairs unresearched** — fall back to the distance formula, visibly.
- **13 of 30 resorts have estimated terrain data.**
- ~~`date_search.search_date_range()`'s DEFAULT flight function is still date-blind~~ **Resolved this session** — `POST /trips/search-dates` (new) wires a live `flight_cost_fn` AND `accommodation_cost_fn` into `search_date_range()` whenever `SERPAPI_API_KEY` is present, same as `/trips/search` already did for the fixed-date mode. `search_date_range()`'s own default (no functions passed) is still season-bands-only by design — that's the offline-testable baseline, not a gap.
- **Affiliate programs never verified** for transfer operators — an assumption, not a fact.
- **Frontend prototype (`frontend/prototype/SkiTripOptimizer.jsx`) embeds a JS port of the engine.** Deliberate for a no-backend demo; must be deleted once the real Next.js + FastAPI split exists. A drift-guard test checks the two engines' constants haven't diverged. **`frontend/app/index.html` (new this session) is a SEPARATE, real frontend that calls the actual FastAPI backend** — no embedded engine logic, no mock data. It's a plain HTML/JS page, not the eventual Next.js app, but it's real in the sense that matters (talks to the live API, live pricing included) where the prototype never was. Once a real Next.js app exists, both `SkiTripOptimizer.jsx` and this page should be retired in its favor.

---

## 8. Immediate priorities

1. ~~Run the code~~ **Done** — venv set up, `requirements.txt` installed, `pytest tests/ -v` run, 3 real bugs found and fixed (§6 items 11–13).
2. ~~First live SerpApi call~~ **Done** — verified live, two real findings recorded (§1, price_insights availability; departure_token round-trip pricing confirmed safe).
3. ~~Wire live flight pricing into the engine~~ **Done this session** — see §5a. `rank_trips()` and `/trips/search` both support it; 224/224 tests pass.
4. ~~Accommodation adapter~~ **Interface + parsing done this session, live call blocked** — see §5b. Needs a provider key (Booking.com's is currently unobtainable for new applicants; Expedia Rapid unevaluated).
5. **Sanity-check estimates against real prices.** Still only the flight leg checked (§1). Most important open question in the project — the blueprint's own risk ranking (§11 of the original blueprint doc) puts this above everything else outstanding. Blocked on accommodation live data for a full check.
6. **Google OAuth credentials** — makes the auth code functional.
7. Then: finish transfer research (20 pairs), verify terrain data (13 resorts), build `routes/trips.py`, wire a live `flight_cost_fn` into `date_search.search_date_range()`'s default (currently still date-blind, see known gaps).
