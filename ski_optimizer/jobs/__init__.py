"""
[PHASE 8/9 — not started]

Planned modules:
  - refresh_static_data.py: periodic ski-pass/transfer price refresh
    (these don't have live APIs, per the blueprint's data-architecture
    notes -- this is a scheduled scrape/manual-update job, not a
    request-time adapter call).
  - trip_watcher.py: re-evaluates saved trips as prices/snow conditions
    change, surfacing the blueprint's "move your trip by 2 days, save
    €320, better snow" scenario. Needs db/ (a Trip table to watch) and
    adapters/flight_adapter.py + adapters/snow_adapter.py first.
"""
