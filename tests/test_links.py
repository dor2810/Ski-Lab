"""
Tests for engine/links.py -- pure URL-building logic, no network access
needed (see that module's docstring on why these are search-results
deep links, not booking links for one specific priced itinerary).
"""
import datetime
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.engine.links import (
    google_flights_url, google_hotels_url, alps2alps_search_url,
    equipment_search_url, ski_pass_search_url,
)


def _resort(name):
    return next(r for r in load_resorts() if r.name == name)


def test_google_flights_url_includes_origin_and_destination():
    r = _resort("Livigno")
    url = google_flights_url(r)
    assert url is not None
    assert url.startswith("https://www.google.com/travel/flights?q=")
    decoded = unquote(url)
    assert "from TLV" in decoded


def test_google_flights_url_includes_dates_when_given():
    # tfs= is an opaque base64url protobuf blob (see
    # adapters/google_flights_adapter.py's own docstring and tests for
    # how it was reverse-engineered/verified) -- this test only proves
    # links.py delegates to the structured search_url() builder with the
    # right route/dates, not what's inside the blob.
    r = _resort("Livigno")
    url = google_flights_url(r, datetime.date(2027, 1, 10), datetime.date(2027, 1, 17))
    assert url.startswith("https://www.google.com/travel/flights/search?tfs=")
    assert "&hl=en&curr=EUR" in url


def test_google_flights_url_omits_dates_when_not_given():
    r = _resort("Livigno")
    url = google_flights_url(r)
    decoded = unquote(url)
    assert "through" not in decoded


def test_google_flights_url_is_none_when_no_iata_code_is_parseable():
    r = _resort("Livigno")
    r.nearest_airport = "somewhere, no code"
    assert google_flights_url(r) is None


def test_google_flights_url_joins_multiple_airports_with_or():
    # Some resorts list more than one served airport, e.g. "Geneva (GVA)
    # / Chambery (CMF)" -- the link should offer both, not just the first.
    multi = next(r for r in load_resorts() if r.nearest_airport.count("(") > 1)
    url = google_flights_url(multi)
    decoded = unquote(url)
    assert " or " in decoded


def test_google_hotels_url_includes_resort_and_country():
    r = _resort("Livigno")
    url = google_hotels_url(r)
    assert url.startswith("https://www.google.com/travel/hotels?q=")
    decoded = unquote(url)
    assert "Livigno" in decoded
    assert r.country in decoded


def test_google_hotels_url_is_dated_and_carries_a_ts_param_when_dates_are_given():
    r = _resort("Livigno")
    url = google_hotels_url(r, datetime.date(2027, 1, 10), datetime.date(2027, 1, 17))
    assert url.startswith("https://www.google.com/travel/search?q=")
    assert "&ts=" in url


def test_google_hotels_url_narrows_to_a_property_name_when_given():
    r = _resort("Livigno")
    url = google_hotels_url(r, property_name="Hotel Bucaneve")
    decoded = unquote(url)
    assert "Hotel Bucaneve" in decoded
    assert "Livigno" in decoded


def test_alps2alps_search_url_is_the_real_booking_form():
    # Confirmed live (curl, 200) -- see engine/links.py's own comment on
    # why this is the fixed booking-form URL and not a resort-specific
    # or query-string-prefilled link.
    assert alps2alps_search_url() == "https://booking.alps2alps.com/booking/index"


def test_equipment_search_url_uses_skiset_for_a_covered_country():
    # Chamonix, France -- Skiset's own published coverage includes
    # France (see engine/links.py's _SKISET_COVERED_COUNTRIES comment).
    r = _resort("Chamonix")
    assert equipment_search_url(r) == "https://www.skiset.co.uk/"


def test_equipment_search_url_falls_back_to_a_google_search_for_an_uncovered_country():
    # Bansko, Bulgaria -- outside Skiset's published network (France,
    # Austria, Switzerland, Italy, Andorra, Spain only).
    r = _resort("Bansko")
    url = equipment_search_url(r)
    assert url.startswith("https://www.google.com/search?q=")
    decoded = unquote(url)
    assert "Bansko" in decoded
    assert "Bulgaria" in decoded


def test_ski_pass_search_url_is_a_resort_named_google_search():
    # No single marketplace sells lift passes across resorts -- see
    # this function's own docstring -- so every resort, covered or not,
    # gets the same real search fallback.
    r = _resort("Livigno")
    url = ski_pass_search_url(r)
    assert url.startswith("https://www.google.com/search?q=")
    decoded = unquote(url)
    assert "Livigno" in decoded
    assert "ski pass" in decoded
