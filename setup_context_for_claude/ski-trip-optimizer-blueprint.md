# AI Ski Vacation Optimization System — Project Blueprint

---

## 1. Product Definition

**Problem:** Planning a ski trip means separately researching flights, transfers, resorts, accommodation, passes, rentals, food, weather/snow, and nightlife, then manually stitching them into one coherent trip with a real total cost. No existing tool optimizes the *whole trip* as a system.

**Initial target user:** Israeli intermediate–advanced skiers/snowboarders, budget-aware but not backpackers, booking independently (not through a travel agent), for 1–2 week European ski trips, often in small groups.

**What the MVP should do:** Take structured preferences (budget, dates, duration, skill level, off-piste interest, nightlife interest, transfer tolerance) and a fixed departure airport (Tel Aviv), and return several complete, cost-summed, explained trip options across a curated set of resorts — using real flight/accommodation data where feasible and well-researched estimates where not.

**What it could become:** A full trip construction and monitoring engine — continuously re-optimizing an itinerary as prices, weather, and snow conditions change, and proactively suggesting better trips ("move by 2 days, save €320, better snow").

**Why this differs from Google/Booking/Skyscanner/ChatGPT:**
- Those tools optimize *one leg* of the trip in isolation. None jointly optimizes flight + transfer + stay + pass + rental + food as a single cost-and-fit function.
- ChatGPT can reason and explain but has no live, structured, verified pricing data — it will hallucinate numbers. This system's core differentiator is *grounded* optimization: real/estimated numeric data feeding a deterministic scoring engine, with an LLM only for language and explanation.
- Resort-quality knowledge (off-piste reputation, snow reliability, terrain mix, nightlife) is scattered across forums and blogs; a structured resort database with these axes doesn't really exist in a directly queryable form.

**Core competitive advantage:** The trip optimization engine + the curated ski-domain resort dataset. Flight/hotel data can eventually be bought or scraped by anyone; the hard-to-copy asset is (a) the combinatorial optimizer tuned to ski-trip-specific tradeoffs, and (b) a well-maintained, ski-expert-quality resort knowledge base with an Israeli-traveler lens (relevant airports, common charter routes, Hebrew-speaking community info, etc.).

---

## 2. System Components

**A. User Preference Engine** — captures hard constraints (budget ceiling, date window, min ski days, departure city, max connections) and soft preferences (off-piste weight, nightlife weight, luxury vs budget, transfer tolerance, terrain mix, resort size, preferred countries) as a structured `UserPreference` object. Natural language input is parsed by an LLM into this schema; a form/slider UI can also produce it directly.

**B. Ski Resort Database** — the core IP. Location, elevation/vertical, lift & piste counts, terrain mix (%beginner/intermediate/advanced), off-piste reputation (curated qualitative + quantitative proxy), snow reliability (historical avg snowfall, base elevation, glacier access), nightlife/après-ski rating, family-friendliness, typical accommodation price band, nearest airports + typical transfer time/cost, ski pass price bands. This is largely hand-curated/researched initially, not scraped.

**C. Flight Search** — flight price/schedule/baggage/connections for Israel→Europe routes. See Data Architecture below; this is one of the two hardest data problems.

**D. Airport→Resort Transport** — shuttle, private transfer, train, bus, rental car, taxi; cost + time per mode per resort. Mostly static/researched data (transfer companies publish rate cards), updated periodically, not real-time.

**E. Accommodation** — hotels/apartments/chalets with price, location, distance to lifts, rating. Real-time search via existing affiliate APIs (see Data section) rather than building your own inventory.

**F. Ski Pass** — adult price by resort/area/day-count, with simple seasonal/day-count pricing curves, refreshed a few times per season (mostly static within a season).

**G. Equipment Rental** — ski/board/boots/helmet package pricing tiers (standard/premium) by resort or resort cluster; static/researched.

**H. Food** — modeled as a per-person-per-day budget by profile (budget/normal/luxury) calibrated per country/resort cost-of-living tier, not scraped per-restaurant initially.

**I. Weather/Snow Intelligence** — forecast + historical snow reliability; adjusts scores dynamically as trip dates approach. Only matters for near-term trips; for trips months out, use historical snow reliability, not live forecasts.

---

## 3. Data Architecture — What's Realistic

Being blunt about API availability (don't assume a website means an API exists):

| Data | Source options | API exists? | Scraping needed? | Legal risk | Update frequency | Cost | Reliability |
|---|---|---|---|---|---|---|---|
| Flights (Israel→EU) | Skyscanner/Kiwi (Tequila) API, Amadeus, Duffel, direct airline APIs (El Al, Wizz, easyJet) | Partial — aggregator APIs exist but are commercial/rate-limited; full self-serve real-time search is genuinely hard | Sometimes as fallback, risky | Medium (ToS-dependent) | Minutes-hourly | Paid (per-search or subscription) | Medium |
| Accommodation | Booking.com Affiliate/Demand API, Expedia Rapid API, Hotelbeds | Yes, affiliate APIs exist | Not needed if affiliate approved | Low if using official program | Hourly-daily | Free (rev-share) to paid | High |
| Ski resort static facts | Manual research, resort official sites, OpenSkiMap, Skiresort.info | No unified API | Light scraping / manual curation for launch | Low (facts, not content reproduction) | Rarely changes | Free (labor cost) | High if curated carefully |
| Ski pass prices | Resort/operator websites (e.g., Compagnie des Alpes, Vail Resorts Europe) | No public API generally | Manual/periodic scraping | Low-medium | Seasonal | Free/scrape | Medium |
| Snow/weather | OpenWeatherMap, Meteoblue, Open-Meteo (free), resort snow reports | Yes, several free/cheap options | No | Low | Hourly-daily | Free/cheap | High for weather, medium for snow depth |
| Airport transfers | GoOpti, Alpybus, Skiidy Gonzales, local operators | Rarely public APIs | Manual rate research/light scraping | Low-medium | Seasonal | Free/scrape | Medium |
| Equipment rental | Local shop sites, Skiset, Intersport Rent | Occasionally | Manual/scraping | Low | Seasonal | Free/scrape | Medium |
| Restaurants/nightlife | Google Places API | Yes | No | Low (paid API) | Rarely | Paid (usage-based) | High |

**Bottom line:** Accommodation and weather/snow are the easy parts (real APIs exist). Flights are the hardest continuously-fresh data problem. Ski pass, transfer, and equipment pricing are best treated as *periodically-refreshed static data you maintain*, not live feeds — trying to scrape all of it live for MVP is a trap.

---

## 4. Optimization Engine

**Recommended approach: hybrid, staged.**

1. **Hard constraint filtering (deterministic):** budget ceiling, date window, min ski days, max connections, departure city — eliminate infeasible trips first. This is simple filtering/constraint satisfaction, not ML.
2. **Multi-objective scoring (weighted, personalized):** for surviving candidates, compute a normalized score per dimension (ski quality, price headroom, snow conditions, nightlife, convenience/transfer, accommodation quality, food fit) and combine via a **per-user weight vector**, not a fixed formula. Weights are either (a) set directly by UI sliders, or (b) inferred by an LLM from natural language ("I don't care about price, give me incredible off-piste" → price weight ~0, off-piste weight high) and then applied by the deterministic scorer — the LLM never invents the score itself, only the weight mapping.
3. **Search/enumeration:** for a given date range and budget, the number of realistic trip combinations (resort × dates × flight option × accommodation option × transfer mode) is large but bounded — a brute-force or lightly pruned search (not true ML) over combinations is tractable for MVP scale (dozens of resorts × a handful of flight/hotel candidates each). True combinatorial/constraint optimization (e.g., ILP) only becomes necessary once you're jointly optimizing across many resorts × many date-shifts × many accommodation options at scale (post-MVP "phase 9" territory).

**Why not pure ML:** you don't have training data on what a good trip is yet, and the domain has clean, explainable structure — weighted multi-criteria scoring is more transparent and debuggable, and *transparency of "why" matters to users* (per the product spec's explanation requirement). ML/learning-to-rank becomes valuable later once you have real user click/booking data to learn preference weights from behavior instead of asking for them.

**Where LLM reasoning fits:** turning free text into constraints/weights, and turning the scored, structured trip options into natural-language explanations. Never computing prices or scores itself.

---

## 5. Hard Constraints vs Soft Preferences

**Hard (filter, binary pass/fail):** total budget ceiling, date window, min ski days, departure airport/country, max flight connections, min accommodation rating floor if specified.

**Soft (rank, weighted, continuous):** off-piste emphasis, nightlife emphasis, luxury-vs-budget accommodation, transfer time tolerance, terrain mix match, resort size, snow reliability, preferred countries.

Architecture: run hard filter first (SQL `WHERE` clauses / simple predicate logic) → score remaining candidates → sort by weighted score → return top N with explanations.

---

## 6. Database Schema (initial, PostgreSQL)

Core entities and key relationships:

- `User` (1) → (many) `UserPreference` (versioned per search/session)
- `Country` (1) → (many) `Airport`, (many) `SkiResort`
- `SkiResort` (many) ↔ (many) `Airport` via `ResortAirportTransfer` (cost, duration, mode)
- `SkiResort` (1) → (many) `SkiArea` (some resorts share a lift-linked area)
- `SkiResort` (1) → (many) `Accommodation`, `SkiPass`, `EquipmentRentalOption`
- `SkiResort` (1) → (many) `WeatherForecast`, `SnowReport` (time-series)
- `Flight` — origin/destination `Airport`, price, schedule, connections (fetched live, cached short-term, not permanently stored as truth)
- `Trip` (1) → (many) `TripOption` (a candidate combination) → references one `Flight` + one `Accommodation` + one `Transfer` + one `SkiPass` + one `EquipmentRentalOption` + computed `Price` breakdown + computed `Score`
- `Price` — generic cost-line table (component type, amount, currency, source, fetched_at) so every `TripOption`'s total is auditable/reconstructable.

Use PostgreSQL for the relational core (strong for constraint filtering + joins); add Redis for short-lived flight/accommodation price caching (these are volatile and shouldn't hit source APIs on every request).

---

## 7. Architecture

```
Frontend (web, later mobile)
    ↓
Backend API (FastAPI/Python)
    ↓
Trip Planning Orchestrator
    ├── Preference Parser (LLM: text → structured UserPreference)
    ├── Data Aggregation Layer
    │     ├── Flight adapter (Amadeus/Kiwi/Duffel)
    │     ├── Accommodation adapter (Booking/Expedia affiliate API)
    │     ├── Static resort/pass/transfer/rental data (own DB)
    │     └── Weather/snow adapter (Open-Meteo + resort snow reports)
    ↓
Constraint Filter (hard rules)
    ↓
Optimization/Scoring Engine (weighted multi-objective)
    ↓
Explanation Generator (LLM: structured trip → natural language "why")
    ↓
Response to Frontend
```

**Where the LLM is used:** parsing free-text preferences into structured constraints/weights; generating human-readable explanations and trip comparisons; conversational follow-up ("what if I move 2 days later?"). **Where it is explicitly NOT used:** computing any price, score, or numeric fact — those always come from the structured data layer, so the LLM cannot hallucinate a flight or pass price.

---

## 8. MVP — Be Ruthless

**Build:**
- Structured preference input (form first; NL parsing can come slightly after) for ~30–50 hand-curated European resorts
- Static, researched (not live-scraped) data for: resort attributes, ski pass price bands, transfer cost/time bands, equipment rental bands, food-profile budgets
- One real API integration: either flights (Amadeus/Kiwi self-serve tier) OR accommodation (Booking affiliate) — pick ONE to make genuinely real first, estimate the other
- Deterministic hard-filter + weighted scoring engine
- Top 5–10 ranked complete trips with cost breakdown and a plain-English "why" (can start as templated text, LLM later)

**Explicitly exclude from MVP:** live weather/snow re-ranking, booking/checkout, multi-mode transfer optimization (pick one reasonable mode per resort), user accounts, mobile app, dynamic ski pass pricing, restaurant/nightlife venue-level data (keep it as a resort-level nightlife *rating*, not venue listings), affiliate monetization plumbing, ML-based ranking.

**Required for MVP:** Postgres, one live pricing API (flights or hotels), a spreadsheet-turned-DB of resort/pass/transfer/food data you research yourself, a simple web frontend (form → results), and the scoring engine.

---

## 9. Roadmap

**Phase 0 — Research (1–2 weeks):** Validate flight/accommodation API access (sign up for Amadeus self-service + Booking affiliate program), hand-research 10 resorts deeply as a data-model pilot.
*Deliverable:* confirmed data sources + draft schema.

**Phase 1 — Resort Intelligence DB (2–4 weeks):** Build schema, populate 30–50 resorts with all static attributes.
*Deliverable:* queryable resort DB; Milestone 1.

**Phase 2 — Trip Cost Calculator (2–3 weeks):** Given dates/budget/resort, sum estimated costs (flight/transfer/stay/pass/rental/food) using static/estimated numbers only.
*Deliverable:* Milestone 2.

**Phase 3 — Scoring Engine (2–3 weeks):** Hard filter + weighted soft scoring across the 30–50 resorts.
*Deliverable:* Milestone 3.

**Phase 4 — One Real Live API (3–5 weeks):** Integrate flights or accommodation live pricing, replacing estimates for that leg.
*Deliverable:* Milestone 4 (partial — real for one leg).

**Phase 5 — Second Live API + Frontend Polish (3–5 weeks):** Add the second real integration; build a usable form-based web UI showing ranked trips with breakdowns.
*Deliverable:* usable MVP end-to-end.

**Phase 6 — NL Preference Parsing + Explanations (2–3 weeks):** Add LLM layer for free-text input and generated "why" text.
*Deliverable:* Milestone 6.

**Phase 7 — Weather/Snow Intelligence (2–4 weeks):** Add forecast/historical snow scoring for near-term trips.
*Deliverable:* Milestone 5.

**Phase 8 — Transfer/Equipment depth + more resorts (ongoing):** Scale resort count, add multi-mode transfer comparison.

**Phase 9 — Monetization/affiliate integration + booking links (later):** Only once trip quality is validated.

---

## 10. Milestones (checkable)

1. Given a resort, the system returns all structured attributes from the DB.
2. Given a budget/dates/resort, the system returns an estimated total cost breakdown.
3. Given 30–50 resorts and a preference set, the system returns a ranked list with scores.
4. Given real dates, the system returns at least one live-priced leg (flight or hotel) integrated into the total.
5. The system re-ranks a given trip set when snow/weather data changes.
6. A user can type a free-text description and receive parsed constraints + ranked, explained trip options.
7. (Stretch) The system proposes an alternative ("shift 2 days, save €X, better snow") automatically.

---

## 11. Hardest Problems, Ranked 1–10 (10 = hardest/most project-threatening)

1. **Reliable, affordable, real-time flight pricing (9)** — the single biggest risk; commercial APIs are rate-limited/costly, and Israel-departure routes are a thin market for some aggregators. Solve or de-risk this FIRST (even if via a semi-manual/cached approach for MVP) because it's the piece most likely to make the product feel fake if wrong.
2. **Combining/normalizing prices across providers into one true total (7)** — currency, taxes, fees, cancellation terms differ; needs a consistent "real total cost" definition early.
3. **Ski pass & transfer pricing at scale (6)** — no APIs, manual maintenance burden grows with resort count.
4. **Personalized weighting from natural language (6)** — mapping fuzzy statements to numeric weights reliably; needs careful prompt design + evaluation.
5. **Snow/weather → recommendation impact modeling (5)** — deciding *how much* current snow should move a ranking is a genuine judgment call, easy to get wrong (over- or under-reacting).
6. **Resort data quality/curation at scale (5)** — accurate off-piste/nightlife ratings require real domain expertise; scaling past ~50 resorts without degrading quality is real work.
7. **Accommodation inventory completeness (4)** — affiliate APIs are solid but don't cover every small ski-town guesthouse.
8. **Optimization performance at scale (3)** — not hard at MVP scale; becomes real only with large-scale date-shift search later.
9. **Legal/scraping risk (3)** — mostly avoidable by preferring official APIs/affiliate programs and manual research over scraping.
10. **API cost management (3)** — manageable with caching and choosing one live integration at a time.

**Solve first:** flight pricing strategy (even a semi-manual MVP approach) and the "real total cost" normalization — everything else can be approximated without killing the core magic; those two, if wrong, break user trust immediately.

---

## 12. Complexity Estimates (ranges, one strong dev + AI tooling)

- **Prototype** (static data, no live APIs, scoring engine, 10–20 resorts): **2–4 weeks**
- **MVP** (30–50 resorts, one live API integrated, basic web UI, hard+soft scoring): **2–4 months**
- **Production-ready** (both flight+hotel live, NL parsing, weather/snow intelligence, polished UI, monitoring, decent resort coverage): **6–10 months**

These are wide on purpose — data integration and content curation (resort research) are usually the real time sink, not the code.

---

## 13. Technology Stack

- **Frontend:** Next.js (React) — fast iteration, good for both form-based MVP and later conversational UI.
- **Backend:** Python + FastAPI — strong typing, async, easy to wire in data pipelines and LLM calls.
- **Database:** PostgreSQL — relational integrity for constraint filtering/joins; JSONB columns for flexible attributes.
- **Caching:** Redis — short-TTL cache for volatile flight/hotel prices.
- **Background jobs:** Celery or a simpler task queue (e.g., APScheduler for MVP) for periodic static-data refresh (ski pass/transfer prices).
- **Data pipelines:** simple Python ETL scripts initially; Airflow/Dagster only once refresh jobs multiply.
- **LLM:** Claude via API — preference parsing + explanation generation, with strict structured-output prompting (never for price generation).
- **Optimization:** plain Python weighted scoring for MVP; consider OR-Tools only once true combinatorial search (date-shift × many resorts) is needed.
- **Hosting:** a managed platform (Render/Fly.io/Railway) for MVP speed; migrate to AWS/GCP when scaling.
- **Monitoring:** Sentry (errors) + basic logging/metrics; add more once there's real traffic.
- **Authentication:** Auth.js/Clerk-style managed auth — don't build this yourself.

Rationale throughout: favor managed/hosted pieces that let you move fast now without hard-blocking a later migration to self-hosted infra at scale.

---

## 14. First Prototype

Input: dates, group size, budget, skiing level, off-piste preference, nightlife preference, accommodation preference (all via a simple form, no NL yet).
Database: 30–50 hand-researched European resorts with static cost estimates (no live APIs at all).
Output: top 10 ranked resorts with an estimated total trip cost breakdown, a strengths/weaknesses list, and a short explanation of the match.

This validates the *core magic* (the scoring/ranking + real-feeling cost breakdown) before you spend any effort on the hardest, most expensive part (live flight pricing). It's small enough to build in weeks and honest enough (clearly-labeled estimates) not to mislead users.

---

## 15. Business Models (for later; don't let this distract from validation now)

Affiliate/booking commissions (flights, hotels, transfers, equipment) are the most natural fit long-term since the product's value is in the *combination*, not gatekeeping any single leg. A premium tier (deeper monitoring, price-drop alerts, group trip coordination) is a plausible add-on once retention is proven. Direct resort/travel-agency partnerships make sense once you have real user volume to offer them. Validate the core recommendation quality first — revenue plumbing is trivial to add later and easy to get wrong (biasing rankings toward commission) if added too early.

---

## 16. Long-Term Vision

The end state is a continuously-running optimizer, not a one-shot search: given a loose target (dates window, budget, style), it searches across flight × airport × resort × accommodation × transfer × pass × equipment × food combinations, and proactively resurfaces better options as prices/snow/weather shift ("move 2 days, save €320, better snow"). Technically this means moving from request-time scoring to a persistent trip-tracking layer with scheduled re-evaluation jobs, plus (eventually) true combinatorial optimization across date ranges once the resort/data coverage and live-pricing integrations are mature enough to make large-scale search worthwhile.

---

## What I Would Do Tomorrow

1. Sign up for the Amadeus Self-Service API (free tier) and test a real Tel Aviv → Geneva/Munich/Milan search — this de-risks the hardest problem first.
2. Apply to the Booking.com Affiliate Partner Program (or Expedia Rapid) in parallel.
3. Pick 10 resorts and hand-research every attribute in section 2B as a schema pilot — this will surface what fields are actually easy vs. hard to source.
4. Draft the PostgreSQL schema from section 6 and stand up a local Postgres instance.
5. Build the static cost calculator (Phase 2) with hardcoded numbers for those 10 resorts — no APIs yet.
6. Write the hard-filter + weighted-scoring function against those 10 resorts and sanity-check it against your own intuition as a ski expert.
7. Build the bare-bones form UI (dates/budget/level/off-piste/nightlife) wired to the scoring function.
8. Once that "smells right," scale resort research to 30–50 and wire in whichever live API (flights or hotels) you got approved first.
