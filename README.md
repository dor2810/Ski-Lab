# Ski Lab

Deploys automatically to Render on every push to `main` — see `render.yaml`.

AI-powered ski vacation planning and optimization system, initially for
Israeli travelers going to European ski resorts. See `project-structure.md`
in the original chat output for the full phase-by-phase rationale behind
this layout — this README covers what's actually implemented today.

*Note on naming: the product is branded "Ski Lab" (see the brand sheet
in `frontend/brand/` for the visual identity). The Python package
itself stays `ski_optimizer` -- renaming a package ripples through
every import statement and isn't worth doing for a branding change
alone; the two names coexist.*

## Status: Phase 2 complete (static cost calculator + scoring engine)

Auth backend (registration, login, Google OAuth) is also written — see
`ski_optimizer/api/AUTH_STATUS.md` for its honest, separate status:
code-complete but never executed (this session's sandbox has no
network access to install FastAPI/SQLAlchemy/etc.). Don't assume it
works until you've actually run its tests.

## Run it

```
pip install -r requirements.txt
python -m ski_optimizer.cli.main
```

This runs a demo scenario (Israeli advanced skier, 5 nights, €1500/person
budget, off-piste + nightlife weighted heavily) against the 30-resort
seed database, printing the top 5 ranked trips with full cost breakdowns
-- plus a "fixed resort" mode demo (already know you want to go to
Livigno? see what it costs).

Run tests:
```
python -m pytest tests/ -v
```

## Project layout

```
ski-trip-optimizer/
├── data/
│   └── ski_resort_database_seed.xlsx   # 30-resort hand-researched seed DB
├── ski_optimizer/
│   ├── models.py                        # Resort / UserPreferences / CostBreakdown / TripOption
│   ├── data/
│   │   ├── resort_repository.py         # [done] reads Resort objects from the xlsx
│   │   └── postgres_resort_repository.py  # [Phase 8 stub]
│   ├── adapters/                        # one file per external data source
│   │   ├── base.py                      # shared conventions (auth, caching, error handling)
│   │   ├── response_cache.py            # [DONE] bounded LRU + TTL, swappable backend (Redis later)
│   │   ├── flight_adapter.py            # [DONE] SerpApi Google Flights -- live search + price insights
│   │   ├── accommodation_adapter.py     # [Phase 5 stub]
│   │   ├── transfer_adapter.py          # [Phase 5/8 stub]
│   │   ├── weather_adapter.py           # [Phase 7 stub]
│   │   └── snow_adapter.py              # [Phase 7 stub]
│   ├── engine/
│   │   ├── cost_calculator.py           # [done] static flight/transfer/accommodation/pass/equipment/food estimates
│   │   ├── terrain.py                   # [done] parses free-text terrain column -> structured beg/int/adv split
│   │   ├── scoring.py                   # [done] hard filter + weighted scoring, skill-aware, discovery + fixed-resort modes
│   │   ├── date_search.py               # [DONE] flexible-date "best value in a month" search
│   │   └── reranker.py                  # [Phase 7 stub] weather/snow-driven re-ranking
│   ├── nlp/
│   │   ├── explainer.py                 # [done] TripOption -> plain-English "why" (template today, LLM later)
│   │   └── preference_parser.py         # [Phase 6 stub] free text -> UserPreferences
│   ├── db/                              # SQLAlchemy models
│   │   └── fare_history.py              # [DONE] append-only fare observations + provider history
│   ├── jobs/                            # [Phase 8/9, not started] scheduled refresh + trip watching
│   ├── api/                             # [Phase 6+, not started] FastAPI web layer
│   └── cli/
│       └── main.py                      # [done] demo entrypoint
└── tests/
    └── test_smoke.py                    # [done] 8 passing sanity checks
```

## What's static vs. dynamic (the important part)

**The LLM (and, for now, these static estimates) should never be the
source of truth for a number a user might actually book against.**

| Cost component | Current state | Real source (adapter file, once built) |
|---|---|---|
| Flights | Flat estimate per country, **or live via SerpApi when `SERPAPI_API_KEY` is set** | `adapters/flight_adapter.py` — built; needs a real key to verify |
| Accommodation | Seed spreadsheet rate-card estimate | `adapters/accommodation_adapter.py` (Booking/Expedia, Phase 5) |
| Airport transfer | Distance-based formula | `adapters/transfer_adapter.py` (operator rate cards) |
| Ski pass | Linear per-day approximation | Resort/operator pricing pages (not day-linear in reality) |
| Weather/snow | Static 1-5 rating in the seed data | `adapters/weather_adapter.py` + `adapters/snow_adapter.py` (Phase 7) |

Every stub file says exactly what it will replace and why, in its own
docstring. `engine/` and `cli/` never import an adapter directly by
name that isn't real yet — they only ever call `cost_calculator` and
`scoring`, which is what makes each adapter a drop-in change instead of
a rewrite.

## How the ranking works

1. **Hard filter**: total cost per person must be ≤ budget.
2. **Soft scoring**: six 0-1 dimension scores (ski quality, price, snow,
   nightlife, convenience, accommodation comfort), combined via a
   personalized weight vector (must sum to 1.0). Plain weighted scoring,
   not ML — see the project blueprint for why that's the right call at
   this stage.
3. Two query modes: **discovery** (rank every resort) and **fixed-resort**
   (`UserPreferences.target_resort = "Livigno"` — evaluate just one).

### Skill-aware terrain matching

`ski_quality` isn't one formula — it reweights by the user's skill level:

| Skill | piste size | off-piste rep | terrain match |
|---|---|---|---|
| beginner | 0.20 | 0.05 | 0.75 |
| intermediate | 0.20 | 0.35 | 0.45 |
| advanced | 0.20 | 0.50 | 0.30 |
| expert | 0.15 | 0.55 | 0.30 |

Off-piste reputation is deliberately near-worthless to a beginner who
will never ski it. Weighting it flat across skill levels was actively
distorting beginner rankings (it floated Chamonix and Verbier to the top
of a beginner's list) — that's why the table exists.

Terrain match itself balances **suitability** (how much terrain the
skier can actually ski, cumulative downward — an advanced skier is fine
on a red run) against **challenge** (terrain at or above their level).
Neither alone works: suitability alone ranks a beginner hill top for an
expert; challenge alone ranks Chamonix highly for a beginner who can't
use 46% of it.

**Terrain data is now structured, not parsed from prose.** The seed
spreadsheet has explicit Beginner %/Intermediate %/Advanced % columns
plus a `Terrain Data Quality` flag (`sourced`, `sourced_conflicting`, or
`estimated`) — see `migrate_terrain_columns.py` for how the original
free-text column was converted. 16 of 30 resorts have genuinely
sourced breakdowns, 1 (Zermatt) has published sources that
disagree significantly (flagged `sourced_conflicting`, orange in the
spreadsheet), and the remaining 13 are estimates inferred from
qualitative descriptions (flagged `estimated`, yellow). Every
explanation says plainly which kind of number it's showing rather than
presenting an estimate with the same confidence as a sourced figure.
`engine/terrain.py`'s free-text parser is now a fallback only, for any
future resort added before someone sources real numbers for it.

## Extended resort data

Beyond the core columns, each resort also has: average annual snowfall
(cm), glacier access (free text, not boolean -- "on-piste year-round,"
"off-piste only," and "no glacier" are meaningfully different for trip
planning), typical season dates, terrain park presence, and **Israeli
flight access** -- a deliberately audience-specific field no generic
resort site publishes ("is this easy to reach from Tel Aviv"), covering
things like Innsbruck's current direct scheduled route (serving St.
Anton, Ischgl, Sölden, Obergurgl) and Bansko/Sofia's dedicated Israeli
charter packages.

Same honesty policy as the terrain data: `extended_data_quality` per
resort is `sourced`, `sourced_conflicting` (Ischgl's snowfall sources
disagree by more than 2x -- 236cm to 543cm depending on source), `mixed`
(some of the 5 fields sourced, others estimated), or `estimated`. The
flight-access field especially should be treated as a starting signal,
not a live route database -- airline routes change season to season;
see `data/migrations/002_extended_data.py` for exactly what was sourced
vs. inferred, and re-verify anything time-sensitive before a real trip.



- Ski days == trip nights (no separate travel-day handling yet).
- 13 of 30 resorts' terrain splits are estimates inferred from prose
  descriptions rather than a published numeric breakdown (flagged
  `estimated` in the spreadsheet and in every explanation that uses
  them) — worth prioritizing in a verification pass.
- European piste grading isn't standardized across countries, so a
  French "red" and an Austrian "red" aren't strictly comparable — terrain
  percentages are approximate even for the "sourced" rows.
- **Rankings are budget-sensitive by design.** `price_score = 1 -
  cost/budget`, so raising your budget compresses price differences and
  lets the other dimensions dominate — a €1,200 search returns Pamporovo
  and Bansko first, while the same weights at €3,000 return St. Anton and
  Ischgl. This is arguably correct (price *should* matter less when you
  have more of it), but it's a real behavior worth knowing about: two
  users with identical preferences and different budgets get genuinely
  different orderings, not just rescaled scores.
- No date-window / snow-forecast intelligence yet (`engine/reranker.py`, Phase 7).
- No flight connection count / max-1-stop constraint yet (needs live
  flight data first — `adapters/flight_adapter.py`, Phase 4).
