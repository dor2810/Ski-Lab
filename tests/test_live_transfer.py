"""
Live transfer pricing, and pickup times that match the actual flight.

Owner, 2026-08-29: "update the transfer price and data when it
displays it not only in the link so you have the updated price. and
show the live label so people know it is fine. Do you care about the
time of landing in the suggested flight to the time of the transfer
you recommend. if not take that"

Answer to the second half was NO -- _ASSUMED_PICKUP_TIME was a
hardcoded "14:00" and the code said so out loud ("since no real flight
time is tracked"). Both providers DO return arrival times (Kiwi's
outbound.arrivalTime, Google's parsed arrival); FlightOption just
never kept them. Quoting a 14:00 pickup for a flight that lands at
21:40 is a wrong number, and a wrong number is worse than a gap.
"""
import datetime

import pytest

from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.models import (
    CostBreakdown,
    TransferQuote,
    TransferSearchResult,
)

OUT = datetime.date(2027, 1, 16)
BACK = datetime.date(2027, 1, 23)


@pytest.fixture
def resort():
    from ski_optimizer.data.alps2alps_locations import ALPS2ALPS_LOCATIONS
    return next(r for r in load_resorts() if r.name in ALPS2ALPS_LOCATIONS)


# --- pickup time follows the flight ---------------------------------

def test_pickup_time_follows_the_flights_arrival_plus_a_buffer():
    from ski_optimizer.api.routes.search import _pickup_time_for
    arrival = datetime.datetime(2027, 1, 16, 21, 40)
    # 21:40 landing + reclaim/meet buffer -> a late-evening pickup,
    # never the old hardcoded 14:00.
    assert _pickup_time_for(arrival) == "22:25"


def test_pickup_time_falls_back_when_no_arrival_is_known():
    from ski_optimizer.api.routes.search import _ASSUMED_PICKUP_TIME, _pickup_time_for
    assert _pickup_time_for(None) == _ASSUMED_PICKUP_TIME


def test_pickup_time_clamps_a_past_midnight_arrival_to_the_same_day():
    # A 23:50 landing + buffer would roll past midnight; the transfer
    # is still booked for that night, not 00:35 the next calendar day
    # (which would quote the WRONG DATE to the operator).
    from ski_optimizer.api.routes.search import _pickup_time_for
    assert _pickup_time_for(datetime.datetime(2027, 1, 16, 23, 50)) == "23:59"


def test_flight_option_carries_the_arrival_time_from_kiwi():
    import json
    from ski_optimizer.adapters import kiwi_mcp_adapter
    payload = json.load(open("tests/fixtures/kiwi_tlv_gva.json"))
    parsed = kiwi_mcp_adapter._parse_itinerary(payload["itineraries"][0])
    assert parsed is not None
    assert parsed.arrival_time is not None
    assert parsed.arrival_time.hour or parsed.arrival_time.minute


# --- live transfer price --------------------------------------------

def _quote(price=180.0, seats=8):
    return TransferQuote(price_eur=price, cost_basis="per_vehicle",
                         vehicle_name="Standard minivan", max_passengers=seats,
                         duration_minutes=95.0)


def test_live_transfer_cost_is_per_person(resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur
    monkeypatch.setattr(
        transfer_adapter, "search_transfer_options",
        lambda **_kw: TransferSearchResult(options=[_quote(price=180.0)]))
    # 180 per VEHICLE, party of 4, both directions -> 90 per person.
    assert live_transfer_cost_eur(resort, OUT, "13:00", group_size=4) == 90.0


def test_live_transfer_cost_degrades_to_none_not_a_guess(resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.adapters.base import AdapterError
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur

    def _raise(**_kw):
        raise AdapterError("rate limited")
    monkeypatch.setattr(transfer_adapter, "search_transfer_options", _raise)
    assert live_transfer_cost_eur(resort, OUT, "13:00", group_size=2) is None


def test_live_transfer_cost_excludes_vehicles_that_cannot_seat_the_party(
        resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur
    monkeypatch.setattr(
        transfer_adapter, "search_transfer_options",
        lambda **_kw: TransferSearchResult(options=[_quote(price=99.0, seats=3)]))
    assert live_transfer_cost_eur(resort, OUT, "13:00", group_size=6) is None


def test_applying_a_live_transfer_price_flags_it_and_rescales_misc():
    from ski_optimizer.engine.cost_calculator import apply_live_transfer_price
    cost = CostBreakdown(flight_eur=300, transfer_eur=40, accommodation_eur=400,
                         ski_pass_eur=250, equipment_eur=110, food_eur=240,
                         misc_eur=67.0)
    updated = apply_live_transfer_price(cost, 62.0)
    assert updated.transfer_eur == 62.0
    assert updated.transfer_price_is_live is True
    assert updated.misc_eur > cost.misc_eur  # buffer follows the bigger trip
    assert cost.transfer_eur == 40 and cost.transfer_price_is_live is False


def test_transfer_info_reports_the_live_price_and_source(resort, monkeypatch):
    # The card's provenance block must say LIVE (not the frozen quote)
    # once a live quote exists -- that is the label the owner asked for.
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_info
    monkeypatch.setattr(
        transfer_adapter, "search_transfer_options",
        lambda **_kw: TransferSearchResult(options=[_quote(price=210.0)]))
    info = live_transfer_info(resort, OUT, "13:00", group_size=2)
    assert info["source"] == "alps2alps_live"
    assert info["price_eur"] == 210.0
    assert info["duration_minutes"] == 95.0
    assert info["vehicles_offered"] == 1


# --- round trip aligned to BOTH flights (2026-08-29) -----------------
# Owner: "make sure the return shuttle fits the flight time". Measured
# against the real API: passing the return FLIGHT DEPARTURE time makes
# Alps2Alps compute the resort pickup itself (17:20 departure -> 11:10
# pickup; 07:00 -> 02:00), which is strictly better than any buffer we
# could invent. Also measured: return_date WITHOUT return_time returns
# NO VEHICLES AT ALL -- a silent empty quote if we ever send one.

def test_round_trip_quote_uses_both_legs_and_the_return_flight_time(resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur
    seen = {}

    def fake(**kw):
        seen.update(kw)
        return {"outbound": TransferSearchResult(options=[_quote(price=200.0)]),
                "return": TransferSearchResult(options=[_quote(price=240.0)])}
    monkeypatch.setattr(transfer_adapter, "search_transfer_round_trip", fake)

    price = live_transfer_cost_eur(resort, OUT, "13:45", group_size=2,
                                   return_date=BACK, return_time="17:20")
    # Real both-leg total, not a doubled one-way guess: (200+240)/2.
    assert price == 220.0
    assert seen["return_date"] == BACK and seen["return_time"] == "17:20"


def test_return_date_without_a_known_flight_time_is_not_sent(resort, monkeypatch):
    # Sending return_date alone returns zero vehicles from the real
    # API, so an unknown return flight time must fall back to a
    # one-way quote doubled (documented), never a half-filled request.
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur
    seen = {}

    def fake(**kw):
        seen.update(kw)
        return {"outbound": TransferSearchResult(options=[_quote(price=200.0)]),
                "return": None}
    monkeypatch.setattr(transfer_adapter, "search_transfer_round_trip", fake)

    price = live_transfer_cost_eur(resort, OUT, "13:45", group_size=2,
                                   return_date=BACK, return_time=None)
    assert seen["return_date"] is None, "return_date must not travel alone"
    assert price == 200.0  # 200 one-way x2 legs / 2 people


def test_transfer_info_reports_both_pickups_and_the_vehicle(resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_info
    monkeypatch.setattr(
        transfer_adapter, "search_transfer_round_trip",
        lambda **kw: {"outbound": TransferSearchResult(options=[_quote(price=200.0)]),
                      "return": TransferSearchResult(options=[_quote(price=240.0)]),
                      "outbound_pickup": "2027-01-16 13:45:00",
                      "return_pickup": "2027-01-23 11:10:00"})
    info = live_transfer_info(resort, OUT, "13:45", group_size=2,
                              return_date=BACK, return_time="17:20")
    assert info["source"] == "alps2alps_live"
    assert info["vehicle_name"] == "Standard minivan"
    assert info["return_pickup_time"] == "11:10"
    assert info["is_private"] is True   # the API sells no shared seats


# --- ski bags are a user choice (2026-08-29) --------------------------
# Owner: "let's add for the search the option to choose if we want to
# come with ski bags or not". This is not cosmetic: measured against
# the live API, the winter default (2 ski bags) restricts the offer to
# minivans, while ski_bags=0 surfaces a 3-seat economy car -- a real
# and cheaper option for someone renting gear at the resort.

def test_ski_bags_choice_reaches_the_provider(resort, monkeypatch):
    from ski_optimizer.adapters import transfer_adapter
    from ski_optimizer.engine.cost_calculator import live_transfer_cost_eur
    seen = {}

    def fake(**kw):
        seen.update(kw)
        return {"outbound": TransferSearchResult(options=[_quote(price=200.0)]),
                "return": None}
    monkeypatch.setattr(transfer_adapter, "search_transfer_round_trip", fake)

    live_transfer_cost_eur(resort, OUT, "13:00", group_size=2, with_ski_bags=False)
    assert seen["ski_bags"] == 0
    seen.clear()
    live_transfer_cost_eur(resort, OUT, "13:00", group_size=3, with_ski_bags=True)
    # One bag per traveller -- what the party actually carries, not the
    # provider's flat seasonal guess of 2.
    assert seen["ski_bags"] == 3


def test_ski_bags_ride_on_the_booking_deeplink(resort):
    from urllib.parse import parse_qs, urlparse
    from ski_optimizer.engine.links import alps2alps_deeplink
    with_bags = alps2alps_deeplink(resort.name, OUT, "13:00", 2, ski_bags=2)
    without = alps2alps_deeplink(resort.name, OUT, "13:00", 2, ski_bags=0)
    # The booking page must open on the SAME basket we priced,
    # otherwise the funnel quietly re-adds the seasonal default and the
    # user sees a different price than the card promised.
    assert parse_qs(urlparse(with_bags).query)["ski_bags"] == ["2"]
    assert parse_qs(urlparse(without).query)["ski_bags"] == ["0"]
