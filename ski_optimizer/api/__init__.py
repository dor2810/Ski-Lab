"""
[PHASE 6+ -- auth + first protected route done]

main.py, security.py, schemas.py, routes/auth.py, routes/google_oauth.py:
real FastAPI app with registration, login, JWT + rotating refresh
tokens, Google OAuth. routes/search.py: the first protected route,
wrapping engine.scoring.rank_trips behind Depends(get_current_user).

See AUTH_STATUS.md for the honest status of what's been run vs. only
syntax-checked (no network access in the sandbox this was built in to
install FastAPI/SQLAlchemy/etc. and actually execute any of it).

routes/trips.py (saved-trip CRUD -- letting a user save a search result
and have jobs/trip_watcher.py, Phase 8/9, watch it for price/snow
changes) is still not built. That's the natural next step once
routes/search.py is verified working for real.
"""
