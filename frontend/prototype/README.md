# Frontend prototype

`SkiTripOptimizer.jsx` is a standalone, runnable UI prototype — a single
React component with the real 30-resort dataset and a JS port of the
Python scoring engine embedded directly in it, so it works without a
backend. It's the fastest way to see and click through the product; it
is NOT the production frontend architecture (see below).

## What's real here

- All 30 resorts, real numbers, generated straight from the seed
  spreadsheet via `regenerate_from_resort_data.py` (never hand-typed —
  run that script again after any spreadsheet update to refresh this file).
- The scoring logic (`computeCost`, `scoreResort`, `rankTrips`) mirrors
  `ski_optimizer/engine/cost_calculator.py` and `scoring.py` line-for-line
  in intent — hard budget filter, skill-weighted ski quality, the same
  six scoring dimensions, auto-normalized weight sliders.
- The terrain-difficulty bar on each result visualizes each resort's
  actual Beginner/Intermediate/Advanced % — not decoration.

## What's a visible, honest stub

- **Sign in / Sign up**: the modal, the Google button, and the email
  form are real UI, but clicking either shows an inline note explaining
  that no backend is connected yet — it never pretends to log someone
  in. Wiring this up for real needs: a registered Google Cloud OAuth app,
  a hosted domain (OAuth redirect URIs can't point at a sandbox), a
  backend to hold sessions, and a database for accounts — all Mac/git/
  hosting work, not frontend work.
- **Fixed-resort mode**: the "Resort" dropdown reuses the same
  `target_resort` concept from `ski_optimizer.engine.scoring`, but (like
  the Python version) it's still date-independent — see
  `engine/date_search.py`'s Phase 4 note.

## Relationship to the target architecture

This is a prototype, not `frontend/` in the production sense described
in `project-structure.md`. The real target is a Next.js app that calls
the FastAPI backend (`ski_optimizer/api/`) instead of embedding engine
logic client-side — that split matters once real, live pricing exists,
since a browser should never be trusted with API keys or be the thing
computing a price a user might book against. This prototype's JS engine
port should be deleted once that real frontend exists, not maintained
alongside it.

## Keeping this in sync

If the resort spreadsheet changes (new resorts, verified terrain data,
corrected prices), re-run:

```
python3 regenerate_from_resort_data.py
```

from this folder (it reads `../../data/ski_resort_database_seed.xlsx`
via the resort_repository loader and rewrites `SkiTripOptimizer.jsx`'s
embedded data block). Don't hand-edit the `RESORTS` array — regenerate it.
