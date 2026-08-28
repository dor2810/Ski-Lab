"""
engine/flight_picks.py -- the Cheapest / Best / Fastest selection.

WHY THESE THREE LABELS: researched 2026-08-28 against what travellers
already know. Skyscanner's default sort is literally called "Best" and
is defined as the trade-off between price and journey convenience, with
Cheapest and Fastest as the other two sorts; Kayak exposes the same
triad. No major flight product labels the fast/premium end "Luxury" --
we have no cabin-class data, so calling it that would imply knowledge
of the seat we don't have.

Every test here is pure and offline: pick_flights is selection maths
over FlightOptions, no network, no adapter.
"""
from ski_optimizer.models import FlightOption
from ski_optimizer.engine.flight_picks import (
    ROLE_BEST,
    ROLE_CHEAPEST,
    ROLE_FASTEST,
    pick_flights,
)


def _opt(price, minutes, airline="SWISS", stops=1, numbers=None):
    return FlightOption(
        price_eur=price,
        origin_airport="TLV",
        destination_airport="GVA",
        airline=airline,
        total_duration_minutes=minutes,
        stops=stops,
        flight_numbers=numbers or [],
    )


def test_empty_input_gives_no_picks():
    assert pick_flights([]) == []


def test_a_single_option_holds_all_three_roles_in_one_pick():
    only = _opt(300, 400)
    picks = pick_flights([only])
    assert len(picks) == 1
    assert picks[0].option is only
    assert set(picks[0].roles) == {ROLE_CHEAPEST, ROLE_BEST, ROLE_FASTEST}


def test_best_is_the_balanced_middle_not_either_extreme():
    # The real shape live searches produce: the cheapest is a day-long
    # ordeal, the fastest costs four times as much, and a middle option
    # is nearly as cheap AND nearly as fast. "Best" must find the
    # middle one -- a naive "best = cheapest" or "best = fastest"
    # implementation fails this test.
    ordeal = _opt(100, 1440)     # cheapest, 24h
    nonstop = _opt(500, 215)     # fastest, pricey
    balanced = _opt(140, 300)    # nearly both
    picks = pick_flights([ordeal, nonstop, balanced])

    by_option = {id(p.option): set(p.roles) for p in picks}
    assert by_option[id(ordeal)] == {ROLE_CHEAPEST}
    assert by_option[id(nonstop)] == {ROLE_FASTEST}
    assert by_option[id(balanced)] == {ROLE_BEST}


def test_roles_collapse_onto_one_option_when_it_wins_everything():
    # When one flight is both the cheapest and the fastest there is no
    # honest second pick -- padding the list with worse options as
    # filler is exactly what this module exists to stop.
    winner = _opt(100, 200)
    slower = _opt(150, 300)
    worse = _opt(400, 250)
    picks = pick_flights([winner, slower, worse])
    assert len(picks) == 1
    assert picks[0].option is winner
    assert set(picks[0].roles) == {ROLE_CHEAPEST, ROLE_BEST, ROLE_FASTEST}


def test_picks_are_ordered_cheapest_first():
    a = _opt(500, 215)
    b = _opt(100, 1440)
    c = _opt(140, 300)
    picks = pick_flights([a, b, c])
    prices = [p.option.price_eur for p in picks]
    assert prices == sorted(prices)


def test_price_tie_breaks_to_the_shorter_journey():
    # Two itineraries at the same fare are not the same offer: the one
    # that gets you there sooner is strictly better and must be the
    # "cheapest" shown.
    slow = _opt(268, 935)
    quick = _opt(268, 440)
    picks = pick_flights([slow, quick])
    cheapest = next(p for p in picks if ROLE_CHEAPEST in p.roles)
    assert cheapest.option is quick


def test_duration_tie_breaks_to_the_cheaper_fare():
    pricey = _opt(600, 215)
    fair = _opt(442, 215)
    picks = pick_flights([_opt(268, 935), pricey, fair])
    fastest = next(p for p in picks if ROLE_FASTEST in p.roles)
    assert fastest.option is fair


def test_input_list_is_not_mutated():
    options = [_opt(500, 215), _opt(100, 1440), _opt(140, 300)]
    snapshot = list(options)
    pick_flights(options)
    assert options == snapshot
