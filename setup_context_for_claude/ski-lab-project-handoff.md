# Ski Lab — Project Handoff

*Compiled to seed a new Claude Project's knowledge base. Upload this alongside the resort spreadsheet and the code zip so a fresh chat has full context without re-explaining anything.*

---

## 1. What this is

An AI-powered ski vacation planning and **optimization engine** — not a recommendation chatbot — initially built for **Israeli travelers** going to European ski resorts. Branded **"Ski Lab."**

Core idea: a user states preferences (budget, dates, skill level, off-piste/nightlife priorities, accommodation tolerance) and the system searches/combines flights, transfers, accommodation, ski pass, equipment, and food into complete ranked trip options with real total cost and plain-English explanations for why each one fits.

**Differentiator vs. Google/Booking/Skyscanner/ChatGPT**: those tools optimize one leg of a trip in isolation, or (for ChatGPT) can reason but has no grounded, structured pricing data and would hallucinate numbers. This system is a **trip optimization engine**: deterministic, explainable scoring over real/estimated structured data, with an LLM used only for language (parsing preferences, explaining results) — never for generating a price or score.

---

## 2. How the person likes to work (important — read this first)

- Comfortable with programming; wants real technical depth, not oversimplified explanations.
- Wants the roadmap/plan kept in mind across sessions, and **wants to be told explicitly if work is drifting off-plan** — this was an early, explicit standing instruction.
- Values honesty about what's actually verified vs. just "looks right" — several real bugs were only caught because of deliberate logic re-reads and adversarial tests (see Section 6), not because everything written was correct on the first pass. Keep doing that; don't just eyeball code and call it done.
- Prefers being offered a small set of concrete next-step options at decision points rather than being left to propose the direction unprompted every time.
- Plans to eventually connect the project to git and run code on a Mac via Claude Code (remote control from the phone), but this hasn't happened yet — **all backend code so far has been written and reviewed but never executed**, because the chat sandbox it was built in has no network access to install dependencies.

---

## 3. Roadmap status (per the original blueprint)

| Phase | Status |
|---|---|
| 0 — Research | Done |
| 1 — Resort intelligence DB | Done (30 resorts, see §4) |
| 2 — Static trip cost calculator | Done, tested |
| 3 — Scoring engine | Done, tested, skill-aware |
| 4 — Live flight API | **Not started** — Amadeus signup was identified as the top-priority next external action, not yet done |
| 5 — Live accommodation API | Not started |
| 6 — AI conversational interface / web frontend | Frontend prototype built (JS-embedded engine, not the real Next.js+FastAPI split yet); NL preference parsing not built |
| 7 — Weather/snow intelligence | Not started (stubbed) |
| 8 — Postgres migration | **Partially started** — auth-only tables (User, RefreshToken, EmailVerificationToken) exist; the full resort/trip schema is still the spreadsheet |
| 9 — Booking/affiliate integration | Not started |

---

## 4. What's actually built

### 4a. Resort database (`data/ski_resort_database_seed.xlsx`)
- **30 resorts** across 8 countries (France, Austria, Switzerland, Italy, Bulgaria, Andorra, Romania, Slovenia, Spain).
- Columns: elevation/vertical/lifts/piste km, **structured** Beginner/Intermediate/Advanced % (real numeric columns, not free text), off-piste/snow/nightlife/family ratings (1–5), nearest airport + transfer time/distance, ski pass + accommodation price estimates, **average annual snowfall (cm)**, **glacier access** (free text, not boolean), **typical season dates**, **terrain park presence**, and **Israeli flight access** (audience-specific — e.g. Innsbruck has a direct scheduled route this season via Israir, serving St. Anton/Ischgl/Sölden/Obergurgl; Bansko/Sofia has dedicated Israeli charter packages and is the best-served route overall).
- Every field is honestly quality-tagged: `sourced` (real citation), `sourced_conflicting` (published sources disagree — e.g. Ischgl's snowfall ranges 236–543cm depending on source), or `estimated` (inferred, not directly sourced). **14 of 30 resorts still have estimated terrain data and need a verification pass** — this is the single most valuable data-quality improvement still outstanding.
- Migration scripts live in `data/migrations/` (`001_terrain_columns.py`, `002_extended_data.py`) so the spreadsheet's history is reproducible, not a black box.

### 4b. Engine (`ski_optimizer/engine/`)
- `cost_calculator.py` — static flight/transfer/accommodation/ski-pass/equipment/food cost estimates. **Flights and accommodation are explicitly placeholder** (flat per-country flight estimate; accommodation is the spreadsheet's researched rate, not live inventory) — flagged everywhere as the two things Phase 4/5 must replace.
- `terrain.py` — structured terrain-mix handling; a free-text parser exists as a fallback only, not the primary path anymore.
- `scoring.py` — hard budget filter + weighted multi-objective scoring across six dimensions (ski quality, price, snow, nightlife, convenience, accommodation). **Skill-aware**: off-piste weighting and terrain-match scoring both shift by skill level (beginner/intermediate/advanced/expert) rather than being flat — this was a real bug fix, see §6. Supports two query modes: **discovery** (rank all resorts) and **fixed-resort** (`target_resort=` — "I already know I want X, what's the deal").
- `date_search.py`, `reranker.py` — honest stubs (raise `NotImplementedError` with a docstring explaining what Phase 4/7 needs to build).

### 4c. Data layer (`ski_optimizer/data/`, `ski_optimizer/models.py`)
- `resort_repository.py` reads `Resort` objects straight from the xlsx — same interface a future Postgres-backed repository will implement, so nothing downstream needs to change when that migration happens.
- `UserPreferences` dataclass now does **real input validation in `__post_init__`** (see §6) — budget/nights/group_size must be positive, skill_level/accommodation_tier/food_profile/equipment_tier must be one of a defined enum set (shared constants, not duplicated between the domain model and the API), weights must be a complete non-negative dict summing to 1.0.

### 4d. Auth backend (`ski_optimizer/api/`, `ski_optimizer/db/`) — **written, reviewed, NEVER EXECUTED**
- FastAPI + SQLAlchemy (SQLite dev / Postgres via `DATABASE_URL`) + Argon2id password hashing + JWT access tokens + **rotating, hashed-at-rest refresh tokens with reuse detection** + Google OAuth via Authlib.
- Routes: `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/me`, `/auth/google/login`, `/auth/google/callback`.
- Sessions live in httpOnly/Secure cookies, never localStorage. CSRF mitigated via a required custom header on state-changing requests.
- `adapters/email_adapter.py` — a working "console" backend (prints instead of sending, good enough to develop/test the verification flow locally) plus a stub for a real provider later.
- **Full honest status, including exactly what's sourced vs. estimated vs. never-tested, lives in `ski_optimizer/api/AUTH_STATUS.md` inside the repo — read that file before trusting any of this.**
- Root cause of untested status: the chat sandbox this was built in has **no network access**, so `pip install fastapi sqlalchemy ...` was never possible. Nothing has been run — not the server, not the test suite.

### 4e. Protected search route (`ski_optimizer/api/routes/search.py`) — also never executed
- `POST /trips/search` wraps `engine.scoring.rank_trips` behind `Depends(get_current_user)` — no valid login cookie, no results.
- Weight validation is forgiving: partial/unnormalized weights get filled with defaults and renormalized rather than rejected; unknown weight keys are rejected.
- `GET /trips/resorts` lists valid resort names for a fixed-resort-mode dropdown.

### 4f. Frontend prototype (`frontend/prototype/SkiTripOptimizer.jsx`)
- A **standalone, runnable** React component — real 30-resort data + a JS port of the Python scoring engine embedded directly, so it works without a backend. This is explicitly a **prototype, not the production architecture** — the real target is Next.js calling the FastAPI backend once live pricing exists (a browser should never hold API keys or compute a bookable price).
- Sign in / Sign up UI is a real, complete-looking component, but clicking either shows an honest inline note that no backend is connected yet — never fakes a successful login.
- `frontend/prototype/regenerate_from_resort_data.py` keeps the embedded data in sync with the spreadsheet via the real `resort_repository` loader (not hand-copied) — re-run this after any spreadsheet edit.

### 4g. Brand identity ("Ski Lab")
- Wordmark: "SKI" + a "LAB" pill tag (reuses the same chip shape already used in the app's UI, e.g. the "Guest" badge).
- Icon: a peak silhouette crossed by a measurement/survey line with tick marks and an amber "sample point" at the summit — literally "the mountain, measured," tying the lab framing to the actual product function.
- Palette: `Crevasse #0B1526` (bg), `Dusk Slope #141F33` / `Panel #182746` (surfaces), `Snowfield #EAF1FB` (text), `Piste Blue #4A8FE0` / `Piste Red #D64545` / `Amber Couloir #E8A548` — these three are **functional data colors** (beginner/intermediate/advanced terrain), not decoration, and shouldn't be repurposed for anything else (e.g. never use Piste Red for error states).
- Type: Space Grotesk (display) / Inter (body) / IBM Plex Mono (data/prices).
- Already applied to the live frontend prototype.

### 4h. Target long-term code structure
Full rationale in the original `project-structure.md` doc from this conversation, but the short version — the repo (`ski_optimizer/` package) is organized so that **every external data source gets its own adapter file**, and nothing else (`engine/`, `api/`) ever touches the outside world directly:
```
ski_optimizer/
├── models.py
├── data/            # repositories — xlsx today, Postgres later, same interface
├── adapters/        # flight, accommodation, transfer, weather, snow — one file each, mostly honest stubs
├── engine/           # cost_calculator, scoring, terrain, date_search, reranker
├── nlp/              # the ONLY place an LLM gets called (explainer.py works today as a template; preference_parser.py stubbed for Phase 6)
├── db/               # SQLAlchemy models — auth tables exist, resort/trip schema doesn't yet
├── jobs/             # stub — scheduled re-checks, not built
├── api/               # FastAPI — auth + search routes real, trips CRUD not built
└── cli/               # working demo entrypoint
```

---

## 5. Testing status

- **53 tests pass** in this environment (`tests/test_smoke.py` — 21, `tests/test_validation.py` — 32) covering the engine, scoring, terrain matching, and the validation fixes from §6.
- **`tests/test_auth.py` and `tests/test_search.py` exist but have never run** — same no-network limitation as the backend itself. Written to standard FastAPI TestClient conventions; expect to find and fix something small the first time they actually execute.
- First real step once there's network access:
  ```
  pip install -r requirements.txt
  pytest tests/ -v
  ```

---

## 6. Real bugs found and fixed this project (worth knowing about, since similar issues could recur)

An explicit code audit (not just "does it look right") found and fixed:

1. **Negative/zero trip_nights produced negative trip costs** that then passed the budget filter and were returned as valid results (a "−3 night trip" priced at −€288 and recommended). Root cause: validation existed only in the API's Pydantic schema, not in the domain model, so the CLI and any direct library use were unprotected.
2. **`group_size=0`** caused a raw `ZeroDivisionError` deep inside the cost calculator instead of a clear error.
3. **Inconsistent invalid-enum handling**: `equipment_tier='deluxe'` raised a `KeyError`, but `food_profile='TYPO'` was *silently* priced as "normal" and `skill_level='expret'` was *silently* scored as "intermediate" — the silent failures are worse than a crash because the output looks plausible.
4. **Off-piste reputation was weighted flat regardless of skill level**, which floated expert-oriented resorts (Chamonix, Verbier) to the top of a *beginner's* ranking, and — worse — gave an unfair boost to resorts that were simply *missing* terrain data (they fell back to an off-piste-heavy formula). Fixed by making the ski-quality weighting skill-dependent and redistributing missing-data weight neutrally.
5. **A test with a 500m elevation-consistency tolerance was decorative** — the largest real deviation across all 30 resorts turned out to be 10m, so the test could never have failed. Tightened to 50m and verified by deliberately planting a bad value to confirm it actually catches errors.
6. A hand-typed fake password hash used for timing-attack mitigation in login would have raised an exception instead of failing cleanly — fixed by generating a real dummy hash at import time instead of hardcoding a malformed one.
7. A regex-based script meant to keep the frontend prototype's embedded data in sync with the spreadsheet **silently failed to write anything** due to a Python escaping bug, while a shallow check made it look like it had worked — caught by deliberately corrupting the file first and confirming the fix actually restored it, rather than trusting the first "looks fine" check.

---

## 7. Explicit "what's next" priority order

1. **Get the backend running for real** once there's network access (the Mac, presumably) — `pip install -r requirements.txt`, run both test files, fix whatever breaks. This is overdue — three layers of backend code (auth, search route, tests) now sit on top of each other, all unexecuted.
2. **Verify the 14 estimated-terrain resorts** — now the single most valuable data-quality gap, since scoring leans on this data more than it used to.
3. **Amadeus flight API signup** (account/console setup, no code) — still the highest-risk unaddressed item per the original blueprint's own risk ranking.
4. **Google OAuth app setup** (Google Cloud Console) — instructions for this were given in-conversation; needs a real project + consent screen + Web application OAuth client with `http://localhost:8000/auth/google/callback` as the exact registered redirect URI.
5. Once the above are real: `routes/trips.py` (saved-trip CRUD), then the actual Next.js frontend calling the real API instead of the JS-embedded prototype.

---

## 8. Files that should accompany this document

- `ski_resort_database_seed.xlsx` — the 30-resort database
- `ski-trip-optimizer.zip` — the full code repository
- `SkiTripOptimizer.jsx` — the standalone frontend prototype (also inside the zip)
- The original full project blueprint (product definition → long-term vision, produced early in this project) — not reproduced in full here since it's long, but its reasoning underlies every phase/priority decision above
