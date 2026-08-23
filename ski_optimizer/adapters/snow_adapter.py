"""
[PHASE 7 — not implemented yet]

Two distinct things this should eventually provide, per the blueprint's
Section 2.I -- keep them separate in the eventual implementation:
  1. Current snow depth / recent snowfall (from resort snow reports)
  2. Historical snow reliability (used for trips far enough out that a
     forecast isn't meaningful yet -- this is what
     Resort.snow_reliability in the seed data approximates today)

Planned interface:

    def get_current_snow_report(resort: Resort) -> SnowReport:
        raise NotImplementedError

    def get_historical_reliability(resort: Resort, month: int) -> float:
        raise NotImplementedError
"""


def get_current_snow_report(*args, **kwargs):
    raise NotImplementedError("Live snow reports are planned for Phase 7 (see module docstring).")


def get_historical_reliability(*args, **kwargs):
    raise NotImplementedError(
        "Historical snow reliability lookup is planned for Phase 7. "
        "Resort.snow_reliability in the seed data is today's static approximation."
    )
