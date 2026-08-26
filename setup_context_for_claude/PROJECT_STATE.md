# Ski Lab — Project State

*Updated 2026-08-27. Supersedes the 2026-08-24 version, which was materially wrong by the end: it described 30 resorts (now 37), 270 tests (now 433), SerpApi as the live-pricing backbone (replaced by keyless scrapers), and a Render deployment (migrated to Cloud Run + Firebase Hosting). Read this first; every number below was re-measured against the running system on the date above, not copied forward.*

---

## 1. The verification ledger — read this before trusting anything

**433 of 433 tests pass.** The project is live in production at **https://ski-lab-app.web.app** (frontend) against **https://ski-lab-api-449641203618.us-central1.run.app** (backend).

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
| Rate limiting | ✅ | 8 tests |

### The one number that matters most, re-measured today

A real production search (Chamonix, 5 ski days, 2 people, Jan 2027) breaks down as:

| Line | € | Source |
|---|---|---|
| Flight | 268 | **live** |
| Accommodation | 201 | **live** |
| **Ski pass** | **352** | estimate |
| Food | 288 | estimate |
| Equipment | 110 | estimate |
| Transfer | 40 | estimate |
| Misc (5% buffer) | 63 | estimate |
| **Total** | **1,322** | **35% live / 65% estimated** |

**65% of the headline number is still an estimate, and the single largest line — the ski pass — is a static guess larger than the live flight price.** The blueprint ranks estimate-vs-reality as the #1 project-threatening risk. Two legs are now genuinely live; the other five are not, and nobody has yet checked a full Ski Lab total against a real booked trip. This remains the most important open question in the project.

---

## 2. What the product is

A **trip optimization engine**, not a recommendation chatbot, for Israeli travelers going to European ski resorts (origin is hardcoded TLV, matching current scope).

**Differentiator:** existing tools optimize one leg in isolation. Ski Lab combines every component into a real total cost, ranked by personalized weights, with an LLM used only for language — never for generating a price or score.

**Two query modes, both built and live:** *Plan my trip* (fixed dates, rank resorts) and *Best value* (flexible dates in a window; ranks resort × date combinations).

**Branding:** "Ski Lab." Palette: Crevasse `#0B1526`, Piste Blue `#4A8FE0`, Piste Red `#D64545`, Amber Couloir `#E8A548`. The three accents are **functional** — they encode beginner/intermediate/advanced terrain — and must not be repurposed (never Piste Red for errors).

---

## 3. Architecture

```
ski_optimizer/
├── models.py              domain objects + shared enum constants
├── data/
│   ├── resort_repository.py       reads Resort objects from the xlsx
│   ├── ski_pass_links.py          37 curated official ticketing URLs
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
│   └── reranker.py                STUB (never built)
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

**The database is ephemeral.** `DATABASE_URL` defaults to `sqlite:///./ski_lab.db`, which on Cloud Run lives inside the container's disposable filesystem. **Every deploy wipes all registered users** — this was hit repeatedly during the 2026-08-26/27 sessions, requiring re-registration of the test account after each redeploy. Real users lose their accounts whenever we ship. `db/database.py` already reads `DATABASE_URL` from the environment, so pointing it at a free-tier Postgres (Neon/Supabase) is a **config change, not a code change**, and keeps the $0 target. Not yet done.

---

## 5. Data assets

- **`ski_resort_database_seed.xlsx`** — **37 resorts**, 9 countries. 22 resorts have `sourced` terrain data, 4 `sourced_conflicting`, **11 still `estimated`**; 9 resorts carry `needs_verification`.
- **`transfer_options.xlsx`** — 62 rows covering 30 airport–resort pairs. **15 of 37 resorts have NO researched transfer option at all** and silently fall back to the distance formula: Bansko, Saalbach-Hinterglemm, Poiana Brasov, Kranjska Gora, Formigal, Krvavec, Astún-Candanchú, Bardonecchia, Passo Tonale, Mayrhofen, Zell am See, Les Arcs, Avoriaz, Les Menuires, Vallnord.
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
- **Database is ephemeral** (§4) — accounts lost on every deploy.
- **Google OAuth is unconfigured.** The "Continue with Google" button is live but cannot work until credentials exist in Google Cloud Console — a step only the project owner can perform.
- **`engine/reranker.py` is a stub.** Weather and snow depth are fetched and *displayed*, but never move the ranking. This is blueprint Milestone 5, unbuilt.
- **`nlp/preference_parser.py` is a stub.** Free-text preference input (blueprint Milestone 6) is unbuilt; the form is the only input path.
- **The "shift 2 days, save €X" auto-suggestion** (blueprint Milestone 7, stretch) is unbuilt.
- **`adapters/snow_adapter.py` is a stub and largely superseded** — ground snow depth now comes from Open-Meteo via `weather_adapter.py`. What it would still add is resort-reported conditions (piste status, recent snowfall reports).
- **`adapters/accommodation_adapter.py` (Booking.com Demand API) has never been called live.** Booking's Managed Affiliate Partner track was paused to new applicants as of 2026-08-24. Superseded in practice by the keyless Google Hotels adapter.
- **Transfer airport consistency:** with no airport specified, transfer resolves to the cheapest airport for a resort, which may not be the one the flight search chose.
- **Affiliate programs never verified** for any operator — an assumption, not a fact. No monetization plumbing exists.

---

## 8. Immediate priorities

1. **Sanity-check estimates against real prices.** Still the most important open question (§1). Ski pass is the biggest and most tractable piece — all 37 official price pages are already curated in `data/ski_pass_links.py`.
2. **Fill the 15 missing transfer routes** (§5) so those resorts' totals stop being partly fictional.
3. **Move off ephemeral SQLite** (§4) — small change, stops real users losing accounts.
4. **Google OAuth credentials** — owner-only step; makes an already-shipped button functional.
5. Then: verify the 11 estimated-terrain resorts; build the reranker (Milestone 5) or NL parsing (Milestone 6).

---

## 9. Working style that has repeatedly paid off here

Every bug worth recording in this project was found by **checking rather than assuming** — and several were found in claims this project had already made about itself. Recent examples:

- A "successful" Firebase deploy that had not actually gone live.
- `_resolve_hotel_mid()` silently rejecting every valid `/m/…` Knowledge Graph ID because it only accepted `/g/…`.
- The conclusion that Skiset had no linkable per-resort URLs — **wrong**, and it was wrong because the check tested the wrong domain and two bad slug guesses. Per-resort research found `skiset.co.uk/ski-resort/{slug}` works directly for most resorts.
- A backend "live pricing broken on Cloud Run" scare that was a malformed test payload, not a real defect.

Test-the-test is not optional here: a passing test proves nothing until it has been seen to fail. Deliberately break the code a test guards, confirm the test catches it, then restore.
