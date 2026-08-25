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
    cheapest_possible_cost, WEEKDAY_NAMES,
)

WEIGHTS = {"ski_quality": 0.30, "price": 0.30, "snow": 0.15,
           "nightlife": 0.10, "convenience": 0.05, "accommodation": 0.10}


def _prefs(**overrides):
    kw = dict(budget_eur_per_person=1300, ski_days=6, group_size=2,
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
                                   datetime.date(2027, 2, 10), nights=6)
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
                                 datetime.date(2027, 2, 3), nights=6) == []


def test_start_weekday_restricts_to_that_weekday_only():
    # A month-wide window, Saturday-only: every result must actually be
    # a Saturday, and there should be about one per week.
    saturday = WEEKDAY_NAMES["saturday"]
    starts = candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
                                   nights=6, start_weekday=saturday)
    assert starts
    assert all(d.weekday() == saturday for d in starts)
    assert len(starts) in (3, 4)  # a ~4-week window, minus the trip length eating the tail


def test_start_weekday_advances_from_a_non_matching_earliest_date():
    # 2027-02-01 is a Monday -- the first Saturday result must be the
    # NEXT Saturday, not silently ignore the constraint on day one.
    saturday = WEEKDAY_NAMES["saturday"]
    assert datetime.date(2027, 2, 1).weekday() != saturday
    starts = candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
                                   nights=6, start_weekday=saturday)
    assert starts[0] == datetime.date(2027, 2, 6)


def test_start_weekday_rejects_out_of_range_values():
    for bad in (-1, 7):
        try:
            candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
                                  nights=6, start_weekday=bad)
            assert False, f"expected ValueError for start_weekday={bad}"
        except ValueError:
            pass


def test_candidate_dates_reject_nonsense_input():
    for kwargs in ({"nights": 0}, {"nights": -2}, {"step_days": 0}):
        try:
            candidate_start_dates(datetime.date(2027, 2, 1), datetime.date(2027, 3, 1),
                                  **{"nights": 6, **kwargs})
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


def test_search_with_impossible_budget_falls_back_to_cheapest_flagged():
    # Nothing fits 150 EUR/person -- search_date_range no longer returns
    # an empty list for this (see its over-budget-fallback docstring),
    # it returns the cheapest option(s) it found, honestly flagged.
    results = search_date_range(load_resorts(), _prefs(budget_eur_per_person=150),
                                datetime.date(2027, 1, 10), datetime.date(2027, 2, 28))
    assert results
    assert all(not t.within_budget for t in results)

    strict = search_date_range(load_resorts(), _prefs(budget_eur_per_person=150),
                               datetime.date(2027, 1, 10), datetime.date(2027, 2, 28),
                               allow_over_budget_fallback=False)
    assert strict == []


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


def test_unavailable_flight_date_falls_back_to_the_static_estimate_not_dropped():
    # CHANGED: a None flight price used to drop the (resort, date) pair
    # entirely. Discovered while swapping to a keyless, scraper-based
    # flight provider (adapters/google_flights_adapter.py, which can get
    # rate-limited/blocked -- a real, likely failure mode, unlike the old
    # paid API's) that this silently emptied the WHOLE result set on any
    # live-pricing hiccup, not just skipped one date -- the exact
    # "silent failure" this project's own conventions rule out
    # everywhere else. A missing flight quote must now degrade to the
    # static estimate, honestly labeled (flight_price_is_live stays
    # False), same as accommodation already did.
    def flight_fn(resort, start, end, prefs):
        return None if start.day % 2 == 0 else 200.0

    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                flight_cost_fn=flight_fn)
    assert results
    even_day_results = [o for o in results if o.start_date.day % 2 == 0]
    assert even_day_results, "dates where the live flight lookup failed should still appear"
    assert all(not o.cost.flight_price_is_live for o in even_day_results)
    odd_day_results = [o for o in results if o.start_date.day % 2 == 1]
    assert all(o.cost.flight_price_is_live for o in odd_day_results)


def test_live_reprice_n_caps_the_number_of_live_calls():
    # The whole point of the cap: with a grid far larger than
    # live_reprice_n, only that many (resort, date) pairs should ever
    # reach the cost_fn -- not every pair in the shortlist x dates grid.
    call_count = {"flight": 0, "accom": 0}

    def flight_fn(resort, start, end, prefs):
        call_count["flight"] += 1
        return 200.0

    def accom_fn(resort, start, end, prefs):
        call_count["accom"] += 1
        return 100.0

    search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                      datetime.date(2027, 3, 1), top_n=500,
                      flight_cost_fn=flight_fn, accommodation_cost_fn=accom_fn,
                      live_reprice_n=5)
    assert call_count["flight"] == 5
    assert call_count["accom"] == 5


def test_live_reprice_n_none_preserves_unbounded_behavior():
    # Default (None) must reprice EVERY evaluated pair, matching the
    # behaviour every existing caller/test was written against.
    call_count = {"flight": 0}

    def flight_fn(resort, start, end, prefs):
        call_count["flight"] += 1
        return 200.0

    search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                      datetime.date(2027, 1, 20), top_n=500,
                      flight_cost_fn=flight_fn)
    # Shortlist (up to 8 resorts) x candidate dates (several) -- far
    # more than any small cap would allow through.
    assert call_count["flight"] > 5


def test_search_responds_to_date_varying_accommodation_prices():
    # Same point as the flight-price test, for the other live-priceable
    # leg: a live accommodation quote that's dramatically cheaper on one
    # date must be able to move the ranking, not be ignored.
    def accom_fn(resort, start, end, prefs):
        if start.month == 1 and start.day >= 20:
            return 50.0  # a steal, per person for the whole stay
        return 2000.0    # deliberately awful everywhere else

    results = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                accommodation_cost_fn=accom_fn)
    best = best_date_per_resort(results)[0]
    assert best.start_date.month == 1 and best.start_date.day >= 20, (
        f"expected the cheap late-January accommodation window, got {best.start_date}"
    )
    assert best.cost.accommodation_eur == 50.0


def test_unavailable_accommodation_date_keeps_the_static_estimate():
    # Unlike flight (dropped when unavailable), a missing accommodation
    # quote must NOT sink an otherwise good date -- it falls back to the
    # static estimate rather than discarding the candidate. See
    # search_date_range's accommodation_cost_fn docstring for why.
    def accom_fn(resort, start, end, prefs):
        return None

    with_fn = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                datetime.date(2027, 2, 28), top_n=500,
                                accommodation_cost_fn=accom_fn)
    without_fn = search_date_range(load_resorts(), _prefs(), datetime.date(2027, 1, 10),
                                   datetime.date(2027, 2, 28), top_n=500)
    assert len(with_fn) == len(without_fn)


def test_include_resorts_restricts_search_date_range_to_exactly_those():
    prefs = _prefs(budget_eur_per_person=2500, include_resorts=["Livigno", "Bansko"])
    results = search_date_range(load_resorts(), prefs, datetime.date(2027, 1, 10),
                                datetime.date(2027, 1, 25), top_n=500)
    names = {o.resort.name for o in results}
    assert names <= {"Livigno", "Bansko"}
    assert names  # something was actually found


def test_include_resorts_bypasses_stage1_top_n_cut_in_search_date_range():
    # Stage 1's fit-based top-N cut (shortlist_size) would normally keep
    # only 1 of these 2 included resorts -- shortlist_size=1 forces that.
    # Both must still appear: the user explicitly picked both, so Stage 1
    # pruning (affordability floor AND the fit top-N cut) must be skipped
    # entirely for an explicit include, not just partially.
    prefs = _prefs(budget_eur_per_person=2500, include_resorts=["Livigno", "Bansko"])
    results = search_date_range(load_resorts(), prefs, datetime.date(2027, 1, 10),
                                datetime.date(2027, 1, 20), top_n=500, shortlist_size=1)
    names = {o.resort.name for o in results}
    assert names == {"Livigno", "Bansko"}


def test_exclude_resorts_removes_just_that_one_from_search_date_range():
    prefs = _prefs(budget_eur_per_person=2500, exclude_resorts=["Val Thorens"])
    results = search_date_range(load_resorts(), prefs, datetime.date(2027, 1, 10),
                                datetime.date(2027, 1, 20), top_n=500)
    names = {o.resort.name for o in results}
    assert "Val Thorens" not in names


def test_start_weekday_threads_through_search_date_range():
    saturday = WEEKDAY_NAMES["saturday"]
    prefs = _prefs(budget_eur_per_person=2500, include_resorts=["Livigno"])
    results = search_date_range(load_resorts(), prefs, datetime.date(2027, 1, 1),
                                datetime.date(2027, 2, 1), top_n=500, start_weekday=saturday)
    assert results
    assert all(o.start_date.weekday() == saturday for o in results)


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
