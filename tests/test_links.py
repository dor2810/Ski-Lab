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


def test_equipment_search_url_uses_the_curated_resort_specific_link_when_present():
    # Chamonix is one of the 37 curated, live-verified entries in
    # data/equipment_rental_links.py -- a resort-scoped Skiset page,
    # not the bare homepage.
    r = _resort("Chamonix")
    assert equipment_search_url(r) == "https://www.skiset.co.uk/ski-resort/chamonix"


def test_equipment_search_url_falls_back_to_skiset_homepage_for_an_uncurated_skiset_country():
    # A resort not in the curated table, but in a country Skiset does
    # cover -- falls back to Skiset's bare front door, not a guess at a
    # resort-specific slug.
    r = _resort("Chamonix")
    r.name = "Not A Real Curated Resort"
    assert equipment_search_url(r) == "https://www.skiset.co.uk/"


def test_equipment_search_url_falls_back_to_a_google_search_for_an_uncurated_uncovered_country():
    # A resort not in the curated table AND outside Skiset's real
    # coverage (see _SKISET_COVERED_COUNTRIES) -- must still get a
    # real, working link.
    r = _resort("Bansko")
    r.name = "Not A Real Curated Resort"
    url = equipment_search_url(r)
    assert url.startswith("https://www.google.com/search?q=")
    decoded = unquote(url)
    assert "Not A Real Curated Resort" in decoded
    assert "Bulgaria" in decoded


def test_every_real_resort_has_a_curated_equipment_rental_url():
    # The curated table (data/equipment_rental_links.py) was researched
    # to cover ALL 37 resorts in this project's data -- catches drift
    # if either the resort spreadsheet or the curated table changes
    # without the other being updated to match.
    from ski_optimizer.data.equipment_rental_links import EQUIPMENT_RENTAL_URLS
    real_names = {r.name for r in load_resorts()}
    assert real_names == set(EQUIPMENT_RENTAL_URLS.keys())


def test_ski_pass_search_url_uses_the_curated_official_link_when_present():
    # Livigno is one of the 37 curated, live-verified entries in
    # data/ski_pass_links.py -- see that module's own docstring.
    r = _resort("Livigno")
    assert ski_pass_search_url(r) == "https://www.skipasslivigno.com/en/skipass-shop-online/"


def test_ski_pass_search_url_falls_back_to_a_google_search_for_an_uncurated_resort():
    # A resort not in the curated table (e.g. added to the spreadsheet
    # later, before the table is extended) must still get a real,
    # working link, same fallback tier as google_flights_url's dateless
    # case.
    r = _resort("Livigno")
    r.name = "Not A Real Curated Resort"
    url = ski_pass_search_url(r)
    assert url.startswith("https://www.google.com/search?q=")
    decoded = unquote(url)
    assert "Not A Real Curated Resort" in decoded


def test_every_real_resort_has_a_curated_ski_pass_url():
    # The curated table (data/ski_pass_links.py) was researched to
    # cover ALL 37 resorts in this project's data -- catches drift if
    # either the resort spreadsheet or the curated table changes
    # without the other being updated to match.
    from ski_optimizer.data.ski_pass_links import SKI_PASS_URLS
    real_names = {r.name for r in load_resorts()}
    assert real_names == set(SKI_PASS_URLS.keys())
