"""
Tests for engine/transfers.py.

Runs fully offline against the curated transfer table -- no API, no key.
"""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.engine.transfers import (
    load_transfer_options, options_for, select_transfer, compare_modes,
    transfer_cost_per_person, transfer_availability_warning,
    TransferOption, PER_PERSON, PER_VEHICLE,
)

OPTIONS = load_transfer_options()

# Known dates for availability tests
SATURDAY = datetime.date(2027, 1, 16)
TUESDAY = datetime.date(2027, 1, 19)


def test_transfer_table_loads():
    assert len(OPTIONS) > 40


def test_every_option_has_a_valid_cost_basis():
    for o in OPTIONS:
        assert o.cost_basis in (PER_PERSON, PER_VEHICLE), f"{o.resort_name}: {o.cost_basis}"
        assert o.cost_eur > 0
        assert o.duration_minutes > 0


def test_per_vehicle_options_declare_a_capacity():
    # Without capacity, multi-vehicle maths silently degrades to one van
    # for any group size.
    for o in OPTIONS:
        if o.cost_basis == PER_VEHICLE:
            assert o.vehicle_capacity and o.vehicle_capacity > 0, o.resort_name


# --- cost basis: the core modelling fix ---

def test_per_person_cost_does_not_change_with_group_size():
    o = next(x for x in OPTIONS if x.cost_basis == PER_PERSON)
    assert o.cost_per_person(1) == o.cost_per_person(8)


def test_per_vehicle_cost_falls_with_group_size():
    # The behaviour the old `group ** 0.3` formula could never produce.
    o = next(x for x in OPTIONS if x.cost_basis == PER_VEHICLE and (x.vehicle_capacity or 0) >= 8)
    assert o.cost_per_person(8) < o.cost_per_person(4) < o.cost_per_person(2)


def test_group_larger_than_one_vehicle_books_several():
    o = TransferOption(
        airport_iata="XXX", resort_name="Test", mode="private_transfer",
        cost_eur=200, cost_basis=PER_VEHICLE, vehicle_capacity=8,
        duration_minutes=90, is_round_trip=False, is_mandatory=False,
        runs_on_days="daily", operator="", data_quality="estimated", source_note="",
    )
    assert o.vehicles_needed(8) == 1
    assert o.vehicles_needed(9) == 2      # 9 people need two vans
    assert o.vehicles_needed(16) == 2
    assert o.vehicles_needed(17) == 3
    # Two vans for 10 costs 400 total, i.e. 40pp -- not 200/10 = 20pp.
    assert o.cost_per_person(10) == 40.0


def test_one_way_quotes_are_doubled_for_round_trip():
    o = TransferOption(
        airport_iata="XXX", resort_name="Test", mode="shared_shuttle",
        cost_eur=50, cost_basis=PER_PERSON, vehicle_capacity=None,
        duration_minutes=90, is_round_trip=False, is_mandatory=False,
        runs_on_days="daily", operator="", data_quality="sourced", source_note="",
    )
    assert o.cost_per_person(2) == 50
    assert o.round_trip_cost_per_person(2) == 100


def test_round_trip_quotes_are_not_doubled_again():
    o = TransferOption(
        airport_iata="XXX", resort_name="Test", mode="shared_shuttle",
        cost_eur=94, cost_basis=PER_PERSON, vehicle_capacity=None,
        duration_minutes=90, is_round_trip=True, is_mandatory=False,
        runs_on_days="daily", operator="", data_quality="sourced", source_note="",
    )
    assert o.round_trip_cost_per_person(2) == 94


def test_rejects_zero_group_size():
    o = OPTIONS[0]
    try:
        o.cost_per_person(0)
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- mandatory modes ---

def test_zermatt_always_selects_the_mandatory_train():
    """
    Zermatt is car-free: road access ends at Tasch and the final leg
    must be rail. A "private transfer to Zermatt" actually terminates at
    Tasch and does NOT remove the train leg, so offering it as an
    alternative would mislead the user.
    """
    for group_size in (1, 2, 8):
        chosen = select_transfer(OPTIONS, "Zermatt", group_size, "GVA")
        assert chosen is not None
        assert chosen.mode == "train"
        assert chosen.is_mandatory


def test_mandatory_overrides_a_contrary_user_preference():
    chosen = select_transfer(OPTIONS, "Zermatt", 4, "GVA",
                             preferred_modes=["private_transfer"])
    assert chosen.mode == "train", "a mandatory mode must not be overridden"


# --- availability ---

def test_weekend_only_shuttle_is_excluded_midweek():
    """
    REGRESSION for the whole reason this was built: Ben's Bus
    Geneva->Val Thorens runs weekends only. In date-range search, which
    compares dozens of start dates, pricing a Tuesday against a shuttle
    that doesn't run that day is simply wrong.
    """
    sat = select_transfer(OPTIONS, "Val Thorens", 2, "GVA", travel_date=SATURDAY)
    tue = select_transfer(OPTIONS, "Val Thorens", 2, "GVA", travel_date=TUESDAY)
    assert sat.mode == "shared_shuttle"
    assert tue.mode != "shared_shuttle", "weekend-only shuttle offered on a Tuesday"


def test_availability_warning_explains_the_midweek_penalty():
    warning = transfer_availability_warning(OPTIONS, "Val Thorens", 2, "GVA",
                                            travel_date=TUESDAY)
    assert warning is not None
    assert "Tuesday" in warning
    assert "SA,SU" in warning


def test_no_warning_when_the_cheapest_option_runs():
    assert transfer_availability_warning(OPTIONS, "Val Thorens", 2, "GVA",
                                         travel_date=SATURDAY) is None


def test_no_date_means_no_availability_filtering():
    # Fixed-date callers that don't supply a date must not be filtered.
    o = next(x for x in OPTIONS if x.runs_on_days not in ("daily", "", None))
    assert o.runs_on(None) is True


def test_daily_services_run_every_day():
    o = next(x for x in OPTIONS if x.runs_on_days == "daily")
    for offset in range(7):
        assert o.runs_on(SATURDAY + datetime.timedelta(days=offset))


# --- user preferences ---

def test_preferred_modes_filter_the_selection():
    # Obergurgl's cheapest option is a public bus; a group with ski bags
    # may reasonably rule that out.
    unrestricted = select_transfer(OPTIONS, "Obergurgl-Hochgurgl", 8, "INN")
    restricted = select_transfer(OPTIONS, "Obergurgl-Hochgurgl", 8, "INN",
                                 preferred_modes=["shared_shuttle", "private_transfer"])
    assert unrestricted.mode == "bus"
    assert restricted.mode in ("shared_shuttle", "private_transfer")


def test_impossible_preference_is_relaxed_rather_than_failing():
    # Better to return a viable transfer the user mildly dislikes than
    # to return nothing at all.
    chosen = select_transfer(OPTIONS, "Val Thorens", 2, "GVA",
                             preferred_modes=["helicopter"])
    assert chosen is not None


def test_mode_flip_is_route_dependent():
    """
    The finding that justifies data over formula: on Geneva->Val Thorens
    the shared shuttle stays cheapest to 8 people, because Geneva's
    shuttle market is competitive. On Innsbruck->Obergurgl private wins
    from 6. No single formula produces both.
    """
    modes = ["shared_shuttle", "private_transfer"]
    vt_8 = select_transfer(OPTIONS, "Val Thorens", 8, "GVA", preferred_modes=modes)
    ob_8 = select_transfer(OPTIONS, "Obergurgl-Hochgurgl", 8, "INN", preferred_modes=modes)
    assert vt_8.mode == "shared_shuttle"
    assert ob_8.mode == "private_transfer"


def test_optimize_for_time_can_differ_from_cost():
    by_cost = select_transfer(OPTIONS, "Obergurgl-Hochgurgl", 2, "INN", optimize_for="cost")
    by_time = select_transfer(OPTIONS, "Obergurgl-Hochgurgl", 2, "INN", optimize_for="time")
    assert by_time.duration_minutes <= by_cost.duration_minutes


# --- lookup and comparison ---

def test_unknown_resort_returns_none():
    assert select_transfer(OPTIONS, "Nonexistent Resort", 2) is None
    assert transfer_cost_per_person(OPTIONS, "Nonexistent Resort", 2) is None


def test_resort_lookup_is_case_and_whitespace_insensitive():
    # Same normalisation lesson as the target_resort bug fixed earlier.
    for probe in ("Val Thorens", "val thorens", "  VAL THORENS  "):
        assert options_for(OPTIONS, probe), f"{probe!r} failed to match"


def test_airport_filter_restricts_results():
    all_vt = options_for(OPTIONS, "Val Thorens")
    gva_only = options_for(OPTIONS, "Val Thorens", "GVA")
    assert 0 < len(gva_only) < len(all_vt)
    assert all(o.airport_iata == "GVA" for o in gva_only)


def test_compare_modes_is_sorted_cheapest_first():
    rows = compare_modes(OPTIONS, "Obergurgl-Hochgurgl", 4, "INN")
    costs = [r["cost_per_person_eur"] for r in rows]
    assert costs == sorted(costs)
    assert all("available_on_date" in r for r in rows)


def test_researched_transfer_range_is_wide():
    """
    Guards the reasoning behind the design: transfers are date-INVARIANT,
    but they are NOT small and NOT uniform. If this range ever collapses,
    someone has replaced real data with a constant -- which is exactly
    what the design says never to do.
    """
    costs = [transfer_cost_per_person(OPTIONS, name, 2)
             for name in {o.resort_name for o in OPTIONS}]
    costs = [c for c in costs if c is not None]
    assert max(costs) / min(costs) > 3, "transfer costs should vary widely by route"


# --- integration with the cost calculator ---

def test_cost_calculator_uses_the_curated_table():
    """
    The engine was initially built standalone and NOT wired in, so all
    this researched data wasn't reaching actual trip costs. This guards
    the integration.
    """
    from ski_optimizer.data.resort_repository import load_resorts
    from ski_optimizer.engine.cost_calculator import (
        transfer_cost_eur_per_person, _formula_transfer_cost,
    )
    zermatt = next(r for r in load_resorts() if r.name == "Zermatt")
    actual = transfer_cost_eur_per_person(zermatt, 2)
    formula = _formula_transfer_cost(zermatt, 2)
    # Zermatt's mandatory rail leg costs roughly double the formula's
    # distance-based guess -- if these ever match, the curated table has
    # stopped being consulted.
    assert actual > formula * 1.5, (
        f"expected the curated Zermatt rail cost, got {actual} (formula: {formula})"
    )


def test_unresearched_resorts_fall_back_to_the_formula():
    # Partial coverage must degrade, not block: 20 of 46 pairs are still
    # unresearched.
    from ski_optimizer.data.resort_repository import load_resorts
    from ski_optimizer.engine.cost_calculator import (
        transfer_cost_eur_per_person, _formula_transfer_cost,
    )
    bansko = next(r for r in load_resorts() if r.name == "Bansko")
    assert transfer_cost_eur_per_person(bansko, 2) == _formula_transfer_cost(bansko, 2)


def test_transfer_cost_reflects_availability_for_a_specific_airport():
    """
    A midweek Geneva->Val Thorens transfer costs more than a Saturday
    one, because the weekend-only shuttle isn't available.

    NOTE the explicit airport_iata. Without it the selector picks the
    cheapest option across ALL airports serving the resort -- which for
    Val Thorens is Lyon (EUR85, daily), so the Geneva weekend constraint
    never bites and this test would pass for the wrong reason. That is
    precisely the airport-consistency gap documented in
    cost_calculator.transfer_cost_eur_per_person: until the flight
    search reports which airport it chose, callers must say.
    """
    from ski_optimizer.engine.transfers import get_transfer_options, transfer_cost_per_person
    options = get_transfer_options()
    sat = transfer_cost_per_person(options, "Val Thorens", 2, airport_iata="GVA",
                                   travel_date=SATURDAY)
    tue = transfer_cost_per_person(options, "Val Thorens", 2, airport_iata="GVA",
                                   travel_date=TUESDAY)
    assert tue > sat, f"Tuesday ({tue}) should cost more than Saturday ({sat})"


def test_airport_agnostic_lookup_can_pick_a_different_airport():
    """
    Documents the known gap rather than hiding it: with no airport
    specified, Val Thorens resolves to the Lyon option (EUR85), not the
    Geneva one (EUR100). Quoting EUR85 alongside a Geneva flight would
    describe a trip nobody is taking. This test exists so the behaviour
    is visible and deliberate, and will need updating when the flight
    search starts reporting its chosen airport.
    """
    from ski_optimizer.engine.transfers import get_transfer_options, select_transfer
    options = get_transfer_options()
    any_airport = select_transfer(options, "Val Thorens", 2)
    geneva = select_transfer(options, "Val Thorens", 2, airport_iata="GVA")
    assert any_airport.airport_iata != geneva.airport_iata
    assert any_airport.round_trip_cost_per_person(2) < geneva.round_trip_cost_per_person(2)
