# Ski Lab — Project State

*Updated 2026-08-27 (second pass, after the ski-pass/transfer research and the light-theme rework). Supersedes the 2026-08-24 version, which was materially wrong by the end: it described 30 resorts (now 37), 270 tests (now 449), SerpApi as the live-pricing backbone (replaced by keyless scrapers), and a Render deployment (migrated to Cloud Run + Firebase Hosting). Read this first; every number below was re-measured against the running system on the date above, not copied forward.*

---

## 1. The verification ledger — read this before trusting anything

**449 of 449 tests pass.** The project is live in production at **https://ski-lab-app.web.app** (frontend) against **https://ski-lab-api-449641203618.us-central1.run.app** (backend).

| Component | Tests | Status |
|---|---|---|
| Engine: cost calculator, scoring, terrain | ✅ | Running (validation alone: 60 tests) |
| Date-range search | ✅ | 33 tests |
| Transfer engine | ✅ | 29 tests |
| Flight adapter (SerpApi, parsing) | ✅ | 28 tests vs. fixture |
| Google Flights adapter (keyless, live) | ✅ | 26 tests + verified live |
| Google Hotels adapter (keyless, live) | ✅ | 31 tests + verified live |
| Weather adapter (Open-Meteo) | ✅ | 22 tests + verified live |
| Auth backend (register/login/JWT) | ✅ | 19 tests, verified live in production |
| Search API routes | ✅ | 41 + 25 tests, verified live in production |
| Response cache | ✅ | 20 tests |
| Transfer adapter (Alps2Alps, live) | ✅ | 16 tests + verified live |
| Booking/search links | ✅ | 16 tests |
| Snow re-ranking (reranker) | ✅ | 10 tests, NEW — was a stub |
| Rate limiting | ✅ | 8 tests |

### The one number that matters most, re-measured today

A real production search (St. Anton am Arlberg, 5 ski days, 2 people, Jan 2027) now breaks down as:

| Line | € | Source |
|---|---|---|
| Flight | live quote | **live** |
| Accommodation | live quote | **live** |
| **Ski pass** | **352.56** | **sourced** — real published price, per-resort peak band |
| Transfer | 50.00 | **sourced** — real operator quote |
| Food | ~288 | estimate (per-day model) |
| Equipment | ~110 | estimate (per-day model) |
| Misc (5% buffer) | derived | estimate |

**As of the 2026-08-27 research pass this is materially better, but not solved.** The ski pass — the largest line — is no longer a guess for 29 of 37 resorts: it is a REAL published price researched from each resort's own ticketing pages (`data/ski_pass_prices.py`). Transfers went from 15 resorts with no researched data at all to 1. So the total is now roughly: two legs live, two legs genuinely sourced, three still estimated (food, equipment, and the 5% misc buffer).

The estimates that were replaced turned out to be meaningfully wrong, which is the real argument for finishing the job: Méribel's pass was overstated by €118, Bardonecchia's by €106, Courchevel's by €94, while Passo Tonale's PEAK was understated by 45% (€224 estimated vs €325 real).

**Still open:** nobody has yet checked a complete Ski Lab total against a real booked trip. Food and equipment remain per-day model estimates. That end-to-end check is still the most important open question in the project.

---

## 2. What the product is

A **trip optimization engine**, not a recommendation chatbot, for Israeli travelers going to European ski resorts (origin is hardcoded TLV, matching current scope).

**Differentiator:** existing tools optimize one leg in isolation. Ski Lab combines every component into a real total cost, ranked by personalized weights, with an LLM used only for language — never for generating a price or score.

**Two query modes, both built and live:** *Plan my trip* (fixed dates, rank resorts) and *Best value* (flexible dates in a window; ranks resort × date combinations).

**Branding:** "Ski Lab." The three piste accents are **functional** — they encode beginner/intermediate/advanced terrain — and must not be repurposed (never Piste Red for errors; `--color-warn` exists for that).

**The UI is LIGHT as of 2026-08-27**, flipped from the original dark navy. The brand anchor was preserved rather than discarded: Crevasse `#0B1526`, the old page background, is now the primary TEXT colour. Design tokens are semantic (`canvas` / `surface` / `sunken` / `ink` / `muted` / `subtle` / `line` / `signal` / `sky`), NOT literal — the old `navy`/`midnight`/`ice` names had started to describe the wrong things, which is exactly the drift that makes a theme change dangerous. All tokens live in `frontend/web/app/globals.css`.

**The search form leads with one-tap trip styles** (`components/TripStylePresets.tsx`), not the six priority sliders. Someone who skis twice a year cannot answer "snow reliability 15%", and being made to decide is where people abandon the form. Each style sets all six weights plus the accommodation/food tiers at once; the sliders remain behind a fine-tune disclosure for anyone who wants them.

---

## 3. Architecture

```
ski_optimizer/
├── models.py              domain objects + shared enum constants
├── data/
│   ├── resort_repository.py       reads Resort objects from the xlsx
│   ├── ski_pass_links.py          37 curated official ticketing URLs
│   ├── ski_pass_prices.py         29 REAL published 6-day pass prices
│   └── equipment_rental_links.py  37 curated rental URLs
├── adapters/              ONE FILE PER EXTERNAL SOURCE — nothing else does I/O
│   ├── google_flights_adapter.py  LIVE, keyless (fast-flights `tfs` protobuf)
│   ├── google_hotels_adapter.py   LIVE, keyless (hand-reverse-engineered `ts`)
│   ├── weather_adapter.py         LIVE, keyless (Open-Meteo), incl. snow depth
│   ├── transfer_adapter.py        LIVE (Alps2Alps public API)
│   ├── flight_adapter.py          SerpApi — kept as unswapped fallback
│   ├── serpapi_hotel_adapter.py   SerpApi — kept as unswapped fallback
│   ├── accommodation_adapter.py   Booking.com Demand API — never called live
│   ├── response_cache.py          bounded LRU + TTL
│   └── snow_adapter.py            STUB (superseded — see §7)
├── engine/                PURE LOGIC — no network, no LLM
│   ├── cost_calculator.py, scoring.py, terrain.py, transfers.py,
│   ├── date_search.py, weather.py, links.py
│   └── reranker.py                snow-condition re-ranking (built 2026-08-27)
├── nlp/
│   ├── explainer.py               templated today, LLM later, same interface
│   └── preference_parser.py       STUB (never built)
├── db/                    SQLAlchemy — auth tables + fare history
├── api/                   FastAPI — auth + protected search routes
└── cli/main.py            working demo entrypoint

frontend/web/              Next.js app (the real frontend; older prototypes deleted)
```

**The load-bearing principle:** every external source is isolated behind an adapter, and `engine/` never sees a provider's response shape.

---

## 4. Infrastructure (changed completely since the last version of this doc)

- **Backend:** Google Cloud Run, `us-central1`, deployed via `gcloud run deploy --source .` from the repo `Dockerfile`. Scale-to-zero (no `--min-instances`), chosen specifically to hold the user's explicit **$0 running cost** requirement. Requires the GCP project on the Blaze plan (already enabled).
- **Frontend:** Firebase Hosting (`ski-lab-app.web.app`), `firebase deploy --only hosting`, served from `frontend/web/out`. GitHub Actions auto-deploys on push to main for frontend paths. **The firebase CLI is NOT global** — use `frontend/web/node_modules/.bin/firebase`.
- **Render is fully gone.** No `render.yaml` behaviour should be assumed anywhere.
- **Known deploy quirk:** a `firebase deploy` can report "Deploy complete!" while the live site still serves the previous version. Always re-verify with a cache-busted curl of the actual JS chunk before claiming a deploy is live.

### The one real infrastructure problem

**The database now SURVIVES deploys (2026-08-28): Litestream → GCS.** The container runs `litestream replicate -exec uvicorn` against `/data/ski_lab.db`, streaming every write to `gs://ski-lab-db-replica-449641203618` (1s sync) and restoring on boot (`run.sh`, `litestream.yml`, Dockerfile). **Verified live**: an account registered before a deploy logged in successfully from the fresh container afterwards — the first time that has ever worked in this project. Constraint: SQLite still has one writer, so the service runs with `--max-instances=1` (fine at current traffic; revisit before real scale). The *long-term* fix is still managed Postgres via `DATABASE_URL` (Neon/Supabase — needs the owner to create the account); when that happens, delete `run.sh`/`litestream.yml` and the Dockerfile's litestream layer.

---

## 5. Data assets

- **`ski_resort_database_seed.xlsx`** — **37 resorts**, 9 countries. 22 resorts have `sourced` terrain data, 4 `sourced_conflicting`, **11 still `estimated`**; 9 resorts carry `needs_verification`.
- **`transfer_options.xlsx`** — **88 rows** (was 62). Only **Astún-Candanchú** now lacks a researched transfer option; its bus line is real and timetabled but no operator publishes a fare, so it stays on the distance formula rather than getting an invented number. Rows may now vary by vehicle capacity within a mode, which the engine already supported and which materially improves accuracy (a 3-seat taxi beats an 8-seat minibus for a couple, and the reverse for a group of eight).
- **`data/ski_pass_prices.py`** — REAL published 6-day adult prices for **29 of 37** resorts, with per-resort peak/shoulder bands where the operator publishes them. Three conventions, chosen deliberately: online/advance rates over counter rates; the LOCAL resort pass over the wider linked-area pass; and per-resort peaks instead of one global multiplier (real ratios run 1.06 to 2.10). The other 8 are documented one by one in `UNPRICED_RESORTS` — mostly structural: Grandvalira and Vallnord price dynamically with no published tariff, and Pamporovo, Formigal and Astún-Candanchú **do not sell a 6-day pass at all**.
- **`data/ski_pass_links.py`** — official ticketing URL for all 37 resorts, each live-verified (HTTP 200 + page content actually about that resort's passes).
- **`data/equipment_rental_links.py`** — resort-scoped rental URL for all 37, same verification standard.

Every data field carries a quality tag: `sourced`, `sourced_conflicting`, or `estimated`.

---

## 6. Key decisions and why

**Live pricing is now keyless.** SerpApi's free quota (250 calls/month) was the binding constraint on live pricing, so both live legs were re-backed onto adapters that need **no API key at all**: `google_flights_adapter.py` (via fast-flights' structured `tfs` protobuf query) and `google_hotels_adapter.py` (hand-reverse-engineered Google Hotels `ts` protobuf param — see that module's docstring for the full derivation and its honest fragility warning). The SerpApi adapters are **kept, unswapped, as fallbacks**. `SERPAPI_API_KEY` is no longer read by the search route.

**Live pricing is still static-first, reprice-top-N.** Rank with the free static estimate, then live-price only the top `live_reprice_n` candidates (default 10), re-sort, return. A resort the live call can't price keeps its static estimate rather than being dropped. `flight_price_is_live` / `accommodation_price_is_live` tag which is which, surfaced in the API and the UI's LIVE/est. badges.

**Amplification gating.** Any lookup that costs a genuinely NEW live request per result is gated to `i == 0` (top result only) — flight booking links, specific-property hotel links, live transfer quotes, weather. Otherwise one search silently multiplies into dozens of live requests.

**Every "View X" link always resolves to something real.** Flights, accommodation, transfer, equipment and lift pass each return a live-specific link when possible and fall back automatically to a real, working search/booking page — never nothing. This is a deliberate contract; `_transfer_search_url` violated it until 2026-08-26 (returned `None` on non-top results) and was fixed.

**Transfers: curated table, not an API,** for cost. The live Alps2Alps quote feeds the *link* only, not `cost.transfer_eur` or the score — making it live for scoring would require a `transfer_cost_fn` threaded through `rank_trips`/`search_date_range`, since transfer cost is computed for every candidate resort, not a capped top-N.

**Persist fare history.** Every search records what it saw, so "which week is cheapest to Innsbruck?" becomes answerable from our own data.

---

## 7. Known gaps — documented, not bugs to re-report

- **65% of the total is still estimated** (§1). The biggest single lever.
- **15 of 37 resorts have zero researched transfer data** (§5).
- **11 resorts have estimated terrain data**, 4 more `sourced_conflicting`.
- ~~Database is ephemeral~~ — fixed 2026-08-28 via Litestream→GCS (§4); Postgres remains the eventual proper home.
- **Google OAuth is unconfigured.** The "Continue with Google" button is live but cannot work until credentials exist in Google Cloud Console — a step only the project owner can perform.
- ~~`engine/reranker.py` is a stub~~ **BUILT 2026-08-27** (blueprint Milestone 5). Snow depth now moves the ranking, weighted by the data's own forecast confidence and capped at 0.7 so one week never erases a resort's accumulated record. Hard-gated on the forecast horizon, so a trip beyond ~15 days out costs zero extra requests and is provably unchanged.
- **`nlp/preference_parser.py` is a stub.** Free-text preference input (blueprint Milestone 6) is unbuilt; the form is the only input path.
- **The "shift 2 days, save €X" auto-suggestion** (blueprint Milestone 7, stretch) is unbuilt.
- **`adapters/snow_adapter.py` is a stub and largely superseded** — ground snow depth now comes from Open-Meteo via `weather_adapter.py`. What it would still add is resort-reported conditions (piste status, recent snowfall reports).
- **`adapters/accommodation_adapter.py` (Booking.com Demand API) has never been called live.** Booking's Managed Affiliate Partner track was paused to new applicants as of 2026-08-24. Superseded in practice by the keyless Google Hotels adapter.
- **Transfer airport consistency:** with no airport specified, transfer resolves to the cheapest airport for a resort, which may not be the one the flight search chose.
- **Affiliate programs never verified** for any operator — an assumption, not a fact. No monetization plumbing exists.

---

## 8. Immediate priorities

1. **Check a complete Ski Lab total against a real booked trip.** Still the most important open question (§1), and now the cheapest it has ever been to answer, since four of seven lines are live or sourced.
2. ~~Move off ephemeral SQLite~~ — done 2026-08-28 (Litestream→GCS, verified). Managed Postgres still wanted eventually (owner must create Neon/Supabase account).
3. **Google OAuth credentials** — owner-only step; makes an already-shipped button functional.
4. **Food and equipment costs** are the last big estimated lines; equipment especially, since `data/equipment_rental_links.py` already names the exact rental page per resort.
5. Then: verify the 11 estimated-terrain resorts; NL preference parsing (Milestone 6); the "shift 2 days, save €X" suggestion (Milestone 7).

---

## 9. Working style that has repeatedly paid off here

Every bug worth recording in this project was found by **checking rather than assuming** — and several were found in claims this project had already made about itself. Recent examples:

- A "successful" Firebase deploy that had not actually gone live.
- `_resolve_hotel_mid()` silently rejecting every valid `/m/…` Knowledge Graph ID because it only accepted `/g/…`.
- The conclusion that Skiset had no linkable per-resort URLs — **wrong**, and it was wrong because the check tested the wrong domain and two bad slug guesses. Per-resort research found `skiset.co.uk/ski-resort/{slug}` works directly for most resorts.
- A backend "live pricing broken on Cloud Run" scare that was a malformed test payload, not a real defect.

Test-the-test is not optional here: a passing test proves nothing until it has been seen to fail. Deliberately break the code a test guards, confirm the test catches it, then restore.
