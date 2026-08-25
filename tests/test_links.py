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
from ski_optimizer.engine.links import google_flights_url, google_hotels_url


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
    r = _resort("Livigno")
    url = google_flights_url(r, datetime.date(2027, 1, 10), datetime.date(2027, 1, 17))
    decoded = unquote(url)
    assert "on 2027-01-10 through 2027-01-17" in decoded


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
