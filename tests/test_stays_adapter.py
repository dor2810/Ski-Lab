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
from ski_optimizer.models import AccommodationFilter

# Real field names and plausible values from the live Val Thorens call.
LIVE_SHAPE = {"hotels": [
    {"name": "Club Med Val Thorens Sensation", "display_price": 175,
     "overall_rating": 4.4, "review_count": 1400, "star_class": 4,
     "amenities": ["SPA", "RESTAURANT", "BAR"],
     "lat": 45.2971, "lng": 6.5806},
    {"name": "Hotel Marielle", "display_price": 565,
     "overall_rating": 4.3, "review_count": 359, "star_class": 4,
     "lat": 45.2985, "lng": 6.5793},
    {"name": "Hotel Altapura", "display_price": 649,
     "overall_rating": 4.4, "review_count": 589, "star_class": None,
     "amenities": [], "lat": 45.2974, "lng": 6.5801},
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
    assert len(result.options) == 3, "the priceless entry must be dropped, not fatal"

    club_med = result.options[0]
    assert club_med.property_name == "Club Med Val Thorens Sensation"
    # display_price is the NIGHTLY rate and is used as-is -- see
    # _parse_hotel for the two measurements that settled this.
    assert club_med.price_eur_per_night == 175.0
    assert club_med.rating == 4.4
    # The field that has been None since the project began.
    assert club_med.distance_to_lifts_km is not None
    assert club_med.distance_to_lifts_km < 0.1


def test_parses_star_class_review_count_and_amenities(monkeypatch):
    """These three arrive on every stays response and were being
    dropped -- they are the only quality attributes the project has."""
    _stub(monkeypatch)
    club_med = stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6).options[0]
    assert club_med.star_class == 4
    assert club_med.review_count == 1400
    assert club_med.amenities == ["SPA", "RESTAURANT", "BAR"]


def test_absent_star_class_stays_none_rather_than_being_guessed(monkeypatch):
    """Verified live 2026-08-30: Hotel Altapura came back with no star
    class while every neighbour had one. An unrated property must not
    be silently demoted to 1 star or promoted to its rating."""
    _stub(monkeypatch)
    options = stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6).options
    altapura = next(o for o in options if o.property_name == "Hotel Altapura")
    assert altapura.star_class is None
    assert altapura.review_count == 589


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


def test_enrichment_carries_star_class_to_primary_results(monkeypatch):
    """The primary scraper cannot see a star class at all, so the whole
    filter depends on the enrichment pass copying it across."""
    from ski_optimizer.engine import cost_calculator
    from ski_optimizer.models import AccommodationOption
    _stub(monkeypatch)
    primary = [AccommodationOption(price_eur_per_night=175.0,
                                   property_name="Club Med Val Thorens Sensation")]
    out = cost_calculator._enrich_options(
        _resort(), datetime.date(2027, 1, 9), nights=6, rooms_needed=1, options=primary)
    assert out[0].star_class == 4
    assert out[0].review_count == 1400
    assert out[0].rating == 4.4


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


# --- Asking the provider to filter, instead of filtering what it sends ---
#
# Measured 2026-08-30 against Kitzbuehel: a plain RELEVANCE search
# returns 12 properties, NONE of which publish a star_class. Asking
# Google for hotel_class=[4,5] returns a DIFFERENT twelve (Hotel Aurach
# and Kitzbuehel Lodge appear, Hotel Kitzhof drops out) -- still with
# no class published. So Google holds the classification and will
# filter on it, but does not always publish it. Filtering only what a
# relevance search happened to return therefore misses real inventory.

def test_a_star_floor_is_sent_to_the_provider(monkeypatch):
    seen = {}
    monkeypatch.setattr(stays_adapter, "_search_raw",
                        lambda *a, **k: (seen.update(k), LIVE_SHAPE)[1])
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6,
        accommodation_filter=AccommodationFilter(min_star_class=4))
    assert seen["hotel_class"] == [4, 5], "a floor means every class at or above it"


def test_a_per_person_cap_becomes_a_per_night_ceiling(monkeypatch):
    """Our cap is per person for the whole stay; the provider wants a
    per-night room price. Rounded UP, never down -- a rounding error
    that excludes a property the traveller could afford is the same
    bug as filtering too hard."""
    seen = {}
    monkeypatch.setattr(stays_adapter, "_search_raw",
                        lambda *a, **k: (seen.update(k), LIVE_SHAPE)[1])
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6, rooms_needed=1,
        group_size=2, accommodation_filter=AccommodationFilter(max_eur_per_person=301.0))
    # EUR301pp x 2 people / 6 nights / 1 room = EUR100.33 a night -> 101
    assert seen["price_max"] == 101


def test_a_rating_floor_snaps_down_to_a_value_the_provider_accepts(monkeypatch):
    """stays only takes 3.5, 4.0 or 4.5. Snapping DOWN keeps the
    provider from over-filtering; our own check still enforces the
    exact number the traveller asked for."""
    seen = {}
    monkeypatch.setattr(stays_adapter, "_search_raw",
                        lambda *a, **k: (seen.update(k), LIVE_SHAPE)[1])
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6,
        accommodation_filter=AccommodationFilter(min_rating=4.3))
    assert seen["min_guest_rating"] == 4.0


def test_property_type_reaches_the_provider(monkeypatch):
    seen = {}
    monkeypatch.setattr(stays_adapter, "_search_raw",
                        lambda *a, **k: (seen.update(k), LIVE_SHAPE)[1])
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6, property_type="VACATION_RENTALS")
    assert seen["property_type"] == "VACATION_RENTALS"


def test_a_provider_filtered_class_is_labelled_not_asserted(monkeypatch):
    """Google filtered to 4-5 star but publishes no class for these
    properties. We may say "Google filtered this to 4 stars or better";
    we may NOT print four stars against a property whose class we were
    never told."""
    unpublished = {"hotels": [{"name": "Hotel Aurach", "display_price": 147,
                               "overall_rating": 4.3, "review_count": 285,
                               "star_class": None, "lat": 47.4, "lng": 12.4}]}
    monkeypatch.setattr(stays_adapter, "_search_raw", lambda *a, **k: unpublished)
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    option = stays_adapter.search_accommodation(
        _resort(), datetime.date(2027, 1, 9), nights=6,
        accommodation_filter=AccommodationFilter(min_star_class=4)).options[0]
    assert option.star_class is None, "never invent the class"
    assert option.star_class_source == "provider_filter"


def test_an_unfiltered_search_sends_no_filters_at_all(monkeypatch):
    """The unfiltered path must keep its exact old request shape."""
    seen = {}
    monkeypatch.setattr(stays_adapter, "_search_raw",
                        lambda *a, **k: (seen.update(k), LIVE_SHAPE)[1])
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    stays_adapter.search_accommodation(_resort(), datetime.date(2027, 1, 9), nights=6)
    for key in ("hotel_class", "price_max", "min_guest_rating", "amenities"):
        assert key not in seen, f"{key} leaked into an unfiltered search"


def test_display_price_is_a_nightly_rate_not_a_stay_total(monkeypatch):
    """REGRESSION GUARD. This adapter divided display_price by `nights`
    for its whole life, on the belief it was a whole-stay total. It is
    not: measured 2026-08-30, our own scraper's per-night figure and
    stays' display_price agree EXACTLY across nine Kitzbuehel
    properties (198/198 ... 598/598), and the value barely moves
    between a 6-night and a 3-night search.

    The division understated every stays-sourced price by a factor of
    the trip length -- a EUR198 Kitzbuehel hotel priced at EUR33 a
    night in January. Harmless while this was a rarely-used fallback;
    load-bearing now that filtered searches come here first."""
    payload = {"hotels": [{"name": "Hotel Kitzbühler Alpen", "display_price": 198,
                           "lat": 47.44, "lng": 12.39}]}
    monkeypatch.setattr(stays_adapter, "_search_raw", lambda *a, **k: payload)
    monkeypatch.setattr(lift_distance, "lift_points_for_resort", lambda resort: [])
    for nights in (1, 3, 6, 10):
        option = stays_adapter.search_accommodation(
            _resort(), datetime.date(2027, 1, 8), nights=nights, use_cache=False).options[0]
        assert option.price_eur_per_night == 198.0, (
            f"nightly rate must not depend on trip length (got {option.price_eur_per_night} "
            f"for {nights} nights)")
