"""
Every backup must actually be reachable -- the owner's complaint,
verified in production 2026-08-29: St. Anton and Ischgl came back
fully estimated while Google, Kiwi AND accommodation all worked from a
residential IP. Root causes, each pinned by a test here:

1. FLIGHTS: when Google returned EMPTY (not "suppressed", not
   "blocked") and Kiwi also failed, SerpApi -- a real API immune to
   our egress IP's reputation -- was never tried. The paid fallback
   only fired on the two explicit block signals.
2. ACCOMMODATION: the chain was google_hotels -> stays, BOTH
   reverse-engineered scrapes of the same Google endpoint family (they
   fail together from a blocked datacenter IP). serpapi_hotel_adapter
   existed, key configured, wired to nothing.
3. OVER-BUDGET VARIANTS: a priced-out resort got exactly ONE flagged
   row, so its card had no arrows -- the owner asked for options even
   when over budget.
"""
import datetime

import pytest

from ski_optimizer.adapters import google_flights_adapter, kiwi_mcp_adapter
from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.models import (
    AccommodationOption,
    AccommodationSearchResult,
    FlightOption,
    FlightSearchResult,
)

OUT = datetime.date(2027, 1, 16)
BACK = datetime.date(2027, 1, 23)


@pytest.fixture
def resort():
    return load_resorts()[0]


@pytest.fixture
def google_empty(monkeypatch):
    monkeypatch.setattr(
        google_flights_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[]))


def _serpapi_flight(price=333.0):
    return FlightOption(
        price_eur=price, origin_airport="TLV", destination_airport="GVA",
        airline="SWISS", total_duration_minutes=400, stops=1,
        flight_numbers=["LX 253"])


def test_flight_price_reaches_serpapi_when_google_is_empty_and_kiwi_fails(
        resort, google_empty, monkeypatch):
    # Kiwi's transport is already disabled offline by conftest.
    # SerpApi must now be consulted even though Google was merely
    # EMPTY, not explicitly blocked.
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    from ski_optimizer.adapters import flight_adapter as serpapi_adapter
    monkeypatch.setattr(
        serpapi_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[_serpapi_flight()]))

    from ski_optimizer.engine.cost_calculator import live_flight_cost_eur
    assert live_flight_cost_eur(resort, OUT, BACK) == 333.0


def test_flight_options_reach_serpapi_when_google_and_kiwi_are_empty(
        resort, google_empty, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    option = _serpapi_flight()
    from ski_optimizer.adapters import flight_adapter as serpapi_adapter
    monkeypatch.setattr(
        serpapi_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[option]))

    from ski_optimizer.engine.cost_calculator import live_flight_options
    picks = live_flight_options(resort, OUT, BACK)
    assert [p.option for p in picks] == [option]


def test_flight_serpapi_is_not_called_without_a_key(
        resort, google_empty, monkeypatch):
    # No key -> the paid path must stay silent (normal state for dev),
    # and the caller sees an honest None, never an invented number.
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    from ski_optimizer.adapters import flight_adapter as serpapi_adapter

    def _fail(**_kw):
        raise AssertionError("serpapi must not be called without a key")
    monkeypatch.setattr(serpapi_adapter, "search_flights", _fail)

    from ski_optimizer.engine.cost_calculator import live_flight_cost_eur
    assert live_flight_cost_eur(resort, OUT, BACK) is None


def _accom_option(price=90.0):
    return AccommodationOption(
        price_eur_per_night=price, property_name="Hotel Test")


def test_accommodation_falls_back_to_serpapi_when_both_scrapers_fail(
        resort, monkeypatch):
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")
    from ski_optimizer.adapters import google_hotels_adapter, stays_adapter
    from ski_optimizer.adapters import serpapi_hotel_adapter

    def _empty(*_a, **_kw):
        return AccommodationSearchResult(options=[])
    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", _empty)
    monkeypatch.setattr(stays_adapter, "search_accommodation", _empty)
    monkeypatch.setattr(
        serpapi_hotel_adapter, "search_accommodation",
        lambda *_a, **_kw: AccommodationSearchResult(options=[_accom_option()]))

    from ski_optimizer.engine.cost_calculator import _live_accommodation_search
    result = _live_accommodation_search(resort, OUT, nights=6, rooms_needed=1)
    assert [o.price_eur_per_night for o in result.options] == [90.0]


def test_accommodation_serpapi_is_not_called_without_a_key(resort, monkeypatch):
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    from ski_optimizer.adapters import google_hotels_adapter, stays_adapter
    from ski_optimizer.adapters import serpapi_hotel_adapter

    def _empty(*_a, **_kw):
        return AccommodationSearchResult(options=[])
    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", _empty)
    monkeypatch.setattr(stays_adapter, "search_accommodation", _empty)

    def _fail(*_a, **_kw):
        raise AssertionError("serpapi hotels must not be called without a key")
    monkeypatch.setattr(serpapi_hotel_adapter, "search_accommodation", _fail)

    from ski_optimizer.engine.cost_calculator import _live_accommodation_search
    result = _live_accommodation_search(resort, OUT, nights=6, rooms_needed=1)
    assert result.options == []


def test_over_budget_resort_gets_multiple_flagged_dates_when_slots_allow():
    # A resort priced out of the budget should still offer the arrows:
    # several dates, every one flagged within_budget=False -- never
    # smuggled in as affordable.
    from ski_optimizer.engine.date_search import search_date_range
    from ski_optimizer.models import UserPreferences

    resorts = load_resorts()
    prefs = UserPreferences(
        budget_eur_per_person=100,  # nothing on earth fits this
        ski_days=5,
        target_resort=resorts[0].name,
    )
    options = search_date_range(
        resorts, prefs,
        earliest_date=datetime.date(2027, 1, 4),
        latest_date=datetime.date(2027, 1, 31),
        top_n=6, pad_with_duplicates=False,
        max_results_per_resort=3,
    )
    same = [t for t in options if t.resort.name == resorts[0].name]
    assert len(same) >= 2, "over-budget resort should still offer several dates"
    assert all(not t.within_budget for t in same)


def test_mixed_budget_search_gives_the_priced_out_resort_variants_too():
    # THE case from the owner's ask: one resort fits the budget, the
    # other doesn't. Before this change the priced-out resort got
    # exactly one flagged teaser row -- a card with no arrows. With
    # slots to spare it must now carry several dates, all flagged.
    from ski_optimizer.engine.cost_calculator import compute_trip_cost
    from ski_optimizer.engine.date_search import search_date_range
    from ski_optimizer.models import UserPreferences

    resorts = load_resorts()
    probe_prefs = UserPreferences(budget_eur_per_person=10000, ski_days=5)
    by_cost = sorted(resorts, key=lambda r: compute_trip_cost(r, probe_prefs).total_eur)
    cheap, pricey = by_cost[0], by_cost[-1]
    cheap_total = compute_trip_cost(cheap, probe_prefs).total_eur
    pricey_total = compute_trip_cost(pricey, probe_prefs).total_eur
    budget = (cheap_total + pricey_total) / 2  # cheap fits, pricey doesn't

    prefs = UserPreferences(
        budget_eur_per_person=budget, ski_days=5,
        include_resorts=[cheap.name, pricey.name],
    )
    options = search_date_range(
        resorts, prefs,
        earliest_date=datetime.date(2027, 1, 4),
        latest_date=datetime.date(2027, 1, 31),
        top_n=8, pad_with_duplicates=False,
        max_results_per_resort=3,
    )
    pricey_rows = [t for t in options if t.resort.name == pricey.name]
    assert len(pricey_rows) >= 2, "priced-out resort should carry variant dates"
    assert len(pricey_rows) <= 3, "still capped per resort"
    assert all(not t.within_budget for t in pricey_rows), \
        "over-budget rows must never be smuggled in as affordable"
    assert any(t.within_budget for t in options), "the affordable resort still leads"


def test_flight_price_reaches_serpapi_when_google_raises(resort, monkeypatch):
    # The one branch found stopping at Kiwi in production: a scraper
    # CRASH (not a clean empty) must still reach the paid API.
    monkeypatch.setenv("SERPAPI_API_KEY", "test-key")

    def _raise(**_kw):
        raise RuntimeError("interstitial page broke the parser")
    monkeypatch.setattr(google_flights_adapter, "search_flights", _raise)
    from ski_optimizer.adapters import flight_adapter as serpapi_adapter
    monkeypatch.setattr(
        serpapi_adapter, "search_flights",
        lambda **_kw: FlightSearchResult(options=[_serpapi_flight(price=345.0)]))

    from ski_optimizer.engine.cost_calculator import live_flight_cost_eur
    assert live_flight_cost_eur(resort, OUT, BACK) == 345.0


def test_every_displayed_row_is_live_priced_when_the_provider_works():
    # The Bansko bug (owner report, 2026-08-29): live prices run HIGHER
    # than static estimates, so un-repriced rows with optimistic
    # estimates outranked their own resort's live-priced dates and won
    # the display slot -- users saw EST rows while live pricing was
    # working perfectly. When the provider can price every pair, every
    # DISPLAYED row must be live, whatever the ranking dance did.
    from ski_optimizer.engine.date_search import search_date_range
    from ski_optimizer.models import UserPreferences

    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=2500, ski_days=5)

    def pricier_live_flight(resort, s, e, _prefs):
        return 400.0  # deliberately above every static estimate

    options = search_date_range(
        resorts, prefs,
        earliest_date=datetime.date(2027, 1, 4),
        latest_date=datetime.date(2027, 1, 31),
        top_n=12, pad_with_duplicates=False,
        live_reprice_n=24, max_results_per_resort=3,
        flight_cost_fn=pricier_live_flight,
    )
    assert options, "search must return rows"
    est_rows = [(t.resort.name, t.start_date) for t in options
                if not t.cost.flight_price_is_live]
    assert est_rows == [], f"displayed rows left estimated: {est_rows}"


def test_second_pass_repricing_reflags_rows_pushed_over_budget():
    # A row selected as within-budget on its static estimate may price
    # over budget once its LIVE cost arrives -- the flag must follow
    # the real number, never the stale estimate.
    from ski_optimizer.engine.date_search import search_date_range
    from ski_optimizer.models import UserPreferences

    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=1500, ski_days=5,
                            target_resort=resorts[0].name)

    def exploding_flight(resort, s, e, _prefs):
        return 5000.0  # every live-priced row is far over budget

    options = search_date_range(
        resorts, prefs,
        earliest_date=datetime.date(2027, 1, 4),
        latest_date=datetime.date(2027, 1, 31),
        top_n=6, pad_with_duplicates=False,
        live_reprice_n=24, max_results_per_resort=3,
        flight_cost_fn=exploding_flight,
    )
    for t in options:
        if t.cost.flight_price_is_live:
            assert not t.within_budget, (
                f"{t.resort.name} {t.start_date}: live total "
                f"{t.cost.total_eur} exceeds budget but is flagged within budget")
