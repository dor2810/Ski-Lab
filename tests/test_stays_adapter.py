"""
Tests for adapters/stays_adapter.py and adapters/lift_distance.py --
the free accommodation backup and the computed distance-to-lifts that
the owner asked for ("This is a ski vacation at the end of the day").

Offline: the network (both `stays` and Overpass) is stubbed. The live
shapes these fixtures mirror were captured 2026-08-28 against Val
Thorens.
"""
import datetime
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters import lift_distance, stays_adapter
from ski_optimizer.adapters import response_cache
from ski_optimizer.adapters.base import AdapterError
from ski_optimizer.data.resort_repository import load_resorts

# Real field names and plausible values from the live Val Thorens call.
LIVE_SHAPE = {"hotels": [
    {"name": "Club Med Val Thorens Sensation", "display_price": 1050,
     "overall_rating": 4.4, "review_count": 1400, "star_class": 4,
     "lat": 45.2971, "lng": 6.5806},
    {"name": "Hotel Marielle", "display_price": 3390,
     "overall_rating": 4.3, "review_count": 359, "star_class": 4,
     "lat": 45.2985, "lng": 6.5793},
    {"name": "No Price Lodge", "display_price": None,
     "overall_rating": 4.9, "lat": 45.30, "lng": 6.58},
]}


@pytest.fixture(autouse=True)
def _clean():
    response_cache.get_cache().clear()
    lift_distance.clear_cache()
    yield
    response_cache.get_cache().clear()
    lift_distance.clear_cache()


def _resort():
    return next(r for r in load_resorts() if r.name == "Val Thorens")


# --- lift distance ---

def test_haversine_matches_a_known_distance():
    # Val Thorens village to Club Med, ~200m apart on the ground.
    km = lift_distance.haversine_km(45.2977, 6.5800, 45.2971, 6.5806)
    assert 0.0 < km < 0.2


def test_nearest_lift_picks_the_closest_point():
    points = [(45.3100, 6.5900, "Far"), (45.2972, 6.5807, "Cairn")]
    km = lift_distance.nearest_lift_km(45.2971, 6.5806, points)
    assert km is not None and km < 0.05


def test_distance_is_none_without_coordinates_or_lifts():
    assert lift_distance.nearest_lift_km(None, 6.58, [(45.0, 6.0, "x")]) is None
    assert lift_distance.nearest_lift_km(45.0, 6.0, []) is None


def test_an_unfrozen_resort_falls_back_to_one_cached_live_fetch(monkeypatch):
    # Resorts in the frozen dataset need no network at all (covered by
    # test_frozen_lift_data_covers_the_database_and_needs_no_network).
    # A resort NOT yet in it -- newly added, generator not re-run --
    # must still work, via a live fetch cached once per process.
    import dataclasses

    calls = {"n": 0}

    def fake_fetch(lat, lon):
        calls["n"] += 1
        return [(45.2972, 6.5807, "Cairn")]

    monkeypatch.setattr(lift_distance, "fetch_lift_points", fake_fetch)
    unlisted = dataclasses.replace(_resort(), name="Brand New Resort")
    lift_distance.lift_points_for_resort(unlisted)
    lift_distance.lift_points_for_resort(unlisted)
    assert calls["n"] == 1


def test_overpass_failure_degrades_to_no_distance(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("overpass down")

    monkeypatch.setattr(lift_distance.requests, "post", boom)
    assert lift_distance.fetch_lift_points(45.0, 6.0) == []


# --- stays adapter ---

def _stub(monkeypatch, payload=LIVE_SHAPE, lifts=((45.2972, 6.5807, "Cairn"),)):
    """Stub BOTH the hotel source and the lift source. Lift points now
    come from the frozen dataset, so that is what gets patched -- the
    live fetch is only a fallback for unlisted resorts."""
    monkeypatch.setattr(stays_adapter, "_search_raw", lambda *a, **k: payload)
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: list(lifts))


def test_parses_properties_with_ratings_and_lift_distance(monkeypatch):
    _stub(monkeypatch)
    result = stays_adapter.search_accommodation(_resort(), datetime.date(2027, 1, 9), nights=6)
    assert len(result.options) == 2, "the priceless entry must be dropped, not fatal"

    club_med = result.options[0]
    assert club_med.property_name == "Club Med Val Thorens Sensation"
    # display_price is the STAY total; the contract everywhere else is
    # per night -- 1050 / 6 nights.
    assert club_med.price_eur_per_night == 175.0
    assert club_med.rating == 4.4
    # The field that has been None since the project began.
    assert club_med.distance_to_lifts_km is not None
    assert club_med.distance_to_lifts_km < 0.1


def test_distance_is_omitted_when_not_requested(monkeypatch):
    _stub(monkeypatch)
    result = stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6, with_lift_distance=False)
    assert all(o.distance_to_lifts_km is None for o in result.options)


def test_results_are_cached(monkeypatch):
    calls = {"n": 0}

    def counting(*a, **k):
        calls["n"] += 1
        return LIVE_SHAPE

    monkeypatch.setattr(stays_adapter, "_search_raw", counting)
    monkeypatch.setattr(lift_distance, "fetch_lift_points", lambda lat, lon: [])
    r = _resort()
    stays_adapter.search_accommodation(r, datetime.date(2027, 1, 9), nights=6)
    second = stays_adapter.search_accommodation(r, datetime.date(2027, 1, 9), nights=6)
    assert calls["n"] == 1 and second.from_cache is True


def test_provider_failure_raises_adapter_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("stays exploded")

    monkeypatch.setattr(stays_adapter, "_search_raw", boom)
    with pytest.raises(AdapterError):
        stays_adapter.search_accommodation(_resort(), datetime.date(2027, 1, 9), nights=6)


# --- engine-level: enrichment of the PRIMARY scraper's options ---

def test_primary_options_are_enriched_with_rating_and_lift_distance(monkeypatch):
    # The gap this closes: our own scraper returns a name and a price
    # and NO coordinates, so distance-to-lifts was unmeasurable on the
    # path that usually answers. stays supplies rating + lat/lng for
    # the same properties, matched by normalized name.
    from ski_optimizer.adapters import google_hotels_adapter
    from ski_optimizer.engine import cost_calculator as cc
    from ski_optimizer.models import AccommodationOption, AccommodationSearchResult

    primary = AccommodationSearchResult(options=[
        AccommodationOption(price_eur_per_night=175.0, property_name="Club Med Val Thorens Sensation"),
        AccommodationOption(price_eur_per_night=999.0, property_name="Unlisted Chalet"),
    ])
    monkeypatch.setattr(google_hotels_adapter, "search_accommodation", lambda *a, **k: primary)
    _stub(monkeypatch)  # stays returns Club Med with rating + coords

    options = cc.live_accommodation_options(_resort(), datetime.date(2027, 1, 9),
                                            nights=6, rooms_needed=1)
    by_name = {o.property_name: o for o in options}

    club_med = by_name["Club Med Val Thorens Sensation"]
    assert club_med.price_eur_per_night == 175.0, "the PRIMARY's price must be kept"
    assert club_med.rating == 4.4, "rating comes from the enrichment source"
    assert club_med.distance_to_lifts_km is not None and club_med.distance_to_lifts_km < 0.1

    # A property the enrichment source doesn't know keeps honest gaps
    # rather than borrowing another hotel's numbers.
    assert by_name["Unlisted Chalet"].rating is None
    assert by_name["Unlisted Chalet"].distance_to_lifts_km is None


def test_frozen_lift_data_covers_the_database_and_needs_no_network(monkeypatch):
    # The production lesson: Overpass 504s from Cloud Run's IP, so
    # runtime lookups failed exactly where the feature had to work.
    # Coordinates are shipped instead -- this asserts both the coverage
    # and that reading them makes NO network call.
    from ski_optimizer.data.ski_lift_locations import SKI_LIFT_COORDS

    def _explode(*a, **k):
        raise AssertionError("frozen lift data must not hit the network")

    monkeypatch.setattr(lift_distance, "fetch_lift_points", _explode)

    resorts = load_resorts()
    covered = [r for r in resorts if r.name in SKI_LIFT_COORDS]
    assert len(covered) >= len(resorts) - 2, (
        f"only {len(covered)}/{len(resorts)} resorts have frozen lift data"
    )
    points = lift_distance.lift_points_for_resort(_resort())
    assert len(points) > 10
    # And it actually measures: Val Thorens is famously ski-in/ski-out.
    km = lift_distance.nearest_lift_km(45.2971, 6.5806, points)
    assert km is not None and km < 0.5
