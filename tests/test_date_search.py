"""
Tests for engine/date_search.py and the season-band cost changes.

These run fully offline -- the funnel was deliberately built to work
against static flight estimates, with live pricing injected via
flight_cost_fn, precisely so the search logic is testable without an
API key.
"""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.models import UserPreferences
from ski_optimizer.engine.cost_calculator import (
    ski_pass_cost, season_band, season_band_multiplier, compute_trip_cost,
    SEASON_PEAK, SEASON_HIGH, SEASON_SHOULDER,
)
from ski_optimizer.engine.date_search import (
    candidate_start_dates, shortlist_resorts, search_date_range,
    best_date_per_resort, price_sensitivity, date_independent_cost,
    cheapest_possible_cost,
)

WEIGHTS = {"ski_quality": 0.30, "price": 0.30, "snow": 0.15,
           "nightlife": 0.10, "convenience": 0.05, "accommodation": 0.10}


def _prefs(**overrides):
    kw = dict(budget_eur_per_person=1300, trip_nights=6, group_size=2,
              accommodation_tier="budget", weights=dict(WEIGHTS))
    kw.update(overrides)
    return UserPreferences(**kw)


# --- season bands ---

def test_season_bands_classify_known_dates():
    assert season_band(datetime.date(2027, 1, 2)) == SEASON_PEAK       # New Year
    assert season_band(datetime.date(2026, 12, 27)) == SEASON_PEAK     # Christmas
    assert season_band(datetime.date(2027, 2, 14)) == SEASON_PEAK      # half-term
    assert season_band(datetime.date(2027, 1, 20)) == SEASON_HIGH
    assert season_band(datetime.date(2027, 3, 25)) == SEASON_SHOULDER
    assert season_band(datetime.date(2026, 12, 5)) == SEASON_SHOULDER


def test_no_date_yields_the_shoulder_baseline():
    # The spreadsheet stores shoulder-season prices, so "no date" must
    # mean "no adjustment" -- otherwise existing fixed-date callers would
    # silently change behaviour.
    assert season_band(None) == SEASON_SHOULDER
    assert season_band_multiplier(None) == 1.0


def test_peak_pass_costs_more_than_shoulder():
    """
    REGRESSION: the spreadsheet stores Ski Arlberg's EUR380 SHOULDER
    price, while main season is EUR450. Without a season band, every
    peak-season trip was understated by ~18% -- which matters most in
    exactly this search mode, where dates are being compared.
    """
    r = next(x for x in load_resorts() if x.name == "St. Anton am Arlberg")
    shoulder = ski_pass_cost(r, 6, datetime.date(2027, 3, 25))
    peak = ski_pass_cost(r, 6, datetime.date(2027, 2, 14))
    assert peak > shoulder
    assert shoulder == r.ski_pass_6day_eur, "shoulder must equal the stored figure"
    assert 440 <= peak <= 460, f"peak {peak} should land near the real EUR450"


def test_pass_cost_without_date_is_unchanged():
    # Back-compatibility: fixed-date callers that pass no date must get
    # exactly what they got before season bands existed.
    for r in load_resorts():
        assert ski_pass_cost(r, 6) == r.ski_pass_6day_eur


def test_trip_cost_rises_in_peak_season():
    r = next(x for x in load_resorts() if x.name == "Bansko")
    p = _prefs()
    shoulder = compute_trip_cost(r, p, start_date=datetime.date(2027, 3, 25))
    peak = compute_trip_cost(r, p, start_date=datetime.date(2027, 2, 14))
    assert peak.total_eur > shoulder.total_eur


# --- candidate dates ---

def test_candidate_dates_fit_entirely_inside_the_window():
    starts = candidate_start_dates(datetime.date(2027, 2, 1),
                                   datetime.date(2027, 2, 10), trip_nights=6)
    assert starts[0] == datetime.date(2027, 2, 1)
    # A 6-night trip starting Feb 5 ends Feb 11, past the window.
    assert starts[-1] == datetime.date(2027, 2, 4)


def test_step_days_coarsens_the_grid():
    # Matters for bootstrapping: with no fare history, every date costs a
    # live API call, so a coarse first pass is much cheaper.
    fine = candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1), 6)
    coarse = candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1), 6, step_days=3)
    assert len(coarse) < len(fine)
    assert coarse[0] == fine[0]


def test_window_shorter_than_the_trip_yields_nothing():
    assert candidate_start_dates(datetime.date(2027, 2, 1),
                                 datetime.date(2027, 2, 3), trip_nights=6) == []


def test_candidate_dates_reject_nonsense_input():
    for kwargs in ({"trip_nights": 0}, {"trip_nights": -2}, {"step_days": 0}):
        try:
            candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
                                  **{"trip_nights": 6, **kwargs})
            assert False, f"expected ValueError for {kwargs}"
        except ValueError:
            pass
    try:
        candidate_start_dates(datetime.date(2027, 3, 1), datetime.date(2027, 2, 1), 6)
        assert False, "expected ValueError for reversed window"
    except ValueError:
        pass


# --- Stage 1: shortlisting ---

def test_shortlist_narrows_the_field():
    resorts = load_resorts()
    sl = shortlist_resorts(resorts, _prefs(), top_n=8)
    assert 0 < len(sl) <= 8
    assert len(sl) < len(resorts)


def test_shortlist_is_empty_when_nothing_is_affordable():
    assert shortlist_resorts(load_resorts(), _prefs(budget_eur_per_person=100)) == []


def test_feasibility_bound_is_optimistic_never_pessimistic():
    """
    Stage 1 may only drop a resort when even its BEST case busts the
    budget. If the bound were pessimistic it could discard trips that
    were actually affordable -- a silent false negative, and the worst
    kind of bug for a search product.
    """
    resorts = load_resorts()
    p = _prefs(budget_eur_per_person=5000)
    for r in resorts:
        bound = cheapest_possible_cost(r, p)
        # The shoulder-season (cheapest) real cost must never be below
        # the optimistic bound.
        actual = compute_trip_cost(r, p, start_date=datetime.date(2027, 3, 25)).total_eur
        assert bound <= actual + 0.01, f"{r.name}: bound {bound} exceeds actual {actual}"


def test_date_independent_cost_excludes_the_ski_pass():
    # The pass is Tier 2 (season-banded), not Tier 3 -- including it here
    # would wrongly treat it as date-invariant.
    r = load_resorts()[0]
    p = _prefs()
    tier3 = date_independent_cost(r, p)
    assert tier3 < compute_trip_cost(r, p).total_eur
    assert tier3 > 0


def test_tier3_costs_are_identical_across_dates():
    """
    The premise the whole funnel rests on: transfer, equipment and food
    do not move with the calendar, so they cannot change which date wins.
    """
    r = load_resorts()[0]
    p = _prefs()
    a = compute_trip_cost(r, p, start_date=datetime.date(2027, 1, 15))
    b = compute_trip_cost(r, p, start_date=datetime.date(2027, 2, 14))
    assert a.transfer_eur == b.transfer_eur
    assert a.equipment_eur == b.equipment_eur
    assert a.food_eur == b.food_eur


# --- full search ---

def test_search_returns_results_within_budget():
    results = search_date_range(load_resorts(), _prefs(),
                                datetime.date(2027, 1, 10), datetime.date(2027, 2, 28))
    assert results
    for opt in results:
        assert 0 < opt.total_eur <= 1300
        assert opt.end_date > opt.start_date


def test_search_results_are_sorted_by_score():
    results = search_date_range(load_resorts(), _prefs(),
                                datetime.date(2027, 1, 10), datetime.date(2027, 2, 28))
    scores = [o.score for o in results]
    assert scores == sorted(scores, reverse=True)


def test_search_with_impossible_budget_returns_nothing():
    assert search_date_range(load_resorts(), _prefs(budget_eur_per_person=150),
                             datetime.date(2027, 1, 10), datetime.date(2027, 2, 28)) == []


def test_search_responds_to_date_varying_flight_prices():
    """
    The point of the whole mode. With a flight function that dips in late
    January and spikes at February half-term, the winner must move to the
    cheap window -- otherwise the search isn't actually finding deals.
    """
    def flight_fn(resort, start, end, prefs):
        base = 200.0
        if start.month == 2 and 8 <= start.day <= 22:
            return base * 1.6
        if start.month == 1 and start.day >= 20:
            return base * 0.75
        return base

    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                flight_cost_fn=flight_fn)
    best = best_date_per_resort(results)[0]
    assert best.start_date.month == 1 and best.start_date.day >= 20, (
        f"expected the late-January dip, got {best.start_date}"
    )


def test_unavailable_flight_date_is_skipped_not_estimated():
    # Returning None must drop the date, never silently substitute an
    # estimate and present it as a real priced option.
    def flight_fn(resort, start, end, prefs):
        return None if start.day % 2 == 0 else 200.0

    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                flight_cost_fn=flight_fn)
    assert results
    assert all(o.start_date.day % 2 == 1 for o in results)


# --- output helpers ---

def test_best_date_per_resort_deduplicates():
    # A raw score sort lets one resort with a cheap week monopolise the
    # whole list; this collapses to one row each.
    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500)
    best = best_date_per_resort(results)
    names = [o.resort.name for o in best]
    assert len(names) == len(set(names))


def test_price_sensitivity_reports_a_real_spread():
    def flight_fn(resort, start, end, prefs):
        return 300.0 if start.month == 2 else 180.0

    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                flight_cost_fn=flight_fn)
    name = results[0].resort.name
    sens = price_sensitivity(results, name)
    assert sens is not None
    assert sens["spread_eur"] > 0
    assert sens["cheapest_eur"] <= sens["most_expensive_eur"]


def test_price_sensitivity_needs_two_dates():
    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500)
    assert price_sensitivity(results, "Nonexistent Resort") is None
