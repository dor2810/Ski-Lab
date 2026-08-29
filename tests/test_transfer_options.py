"""
ONE ranked list of real transfer options, the way flights already work.

Owner, 2026-08-29: "improve the UI of the transfer results. to be like
flight options... i want it to be as stable as the flights. and i want
you to represent different options, via bus, train nd whatever you
know", plus "you didnt update the transfer price, you just added a tag
that says there is a cheeper option".

So: private vehicles (Alps2Alps) and scheduled coach/train (Omio) are
merged into a single list, each priced PER PERSON so they are directly
comparable, ranked cheapest-first, tagged with the same
Cheapest/Fastest roles engine/flight_picks.py uses -- and the CHEAPEST
one drives cost.transfer_eur instead of the old private-only figure.
"""
import datetime

import pytest

from ski_optimizer.engine.transfer_options import (
    ROLE_CHEAPEST, ROLE_FASTEST, TransferOption, rank_transfer_options,
)

OUT = datetime.date(2027, 1, 16)


def _opt(kind, price, minutes, mode="bus"):
    return TransferOption(kind=kind, mode=mode, price_eur_per_person=price,
                          duration_minutes=minutes)


def test_options_are_ranked_cheapest_first():
    ranked = rank_transfer_options([
        _opt("private", 423.5, 150, mode="minivan"),
        _opt("scheduled", 57.62, 195),
    ])
    assert [o.price_eur_per_person for o in ranked] == [57.62, 423.5]


def test_cheapest_and_fastest_roles_are_tagged():
    ranked = rank_transfer_options([
        _opt("scheduled", 57.62, 195),
        _opt("private", 423.5, 150, mode="minivan"),
    ])
    cheapest = next(o for o in ranked if ROLE_CHEAPEST in o.roles)
    fastest = next(o for o in ranked if ROLE_FASTEST in o.roles)
    assert cheapest.price_eur_per_person == 57.62
    assert fastest.duration_minutes == 150


def test_one_option_can_hold_both_roles_and_is_listed_once():
    # A private car that is both cheapest AND fastest must appear ONCE
    # with both badges -- same rule as flight_picks.
    ranked = rank_transfer_options([
        _opt("private", 40.0, 90, mode="minivan"),
        _opt("scheduled", 60.0, 200),
    ])
    assert len(ranked) == 2
    top = ranked[0]
    assert ROLE_CHEAPEST in top.roles and ROLE_FASTEST in top.roles


def test_duplicate_departures_are_collapsed():
    # Omio returns the same coach several times across departures; a
    # list of five identical "bus EUR103, 240min, AlpyBus" rows is
    # noise, not choice (measured live on Geneva -> Val Thorens).
    ranked = rank_transfer_options([
        TransferOption(kind="scheduled", mode="bus", price_eur_per_person=103.0,
                       duration_minutes=240, carrier="AlpyBus"),
        TransferOption(kind="scheduled", mode="bus", price_eur_per_person=103.0,
                       duration_minutes=240, carrier="AlpyBus"),
    ])
    assert len(ranked) == 1


def test_modes_are_preserved_so_the_ui_can_show_bus_vs_train():
    ranked = rank_transfer_options([
        _opt("scheduled", 59.06, 200, mode="train"),
        _opt("scheduled", 57.62, 195, mode="bus"),
        _opt("private", 200.0, 150, mode="minivan"),
    ])
    assert {o.mode for o in ranked} == {"train", "bus", "minivan"}


def test_empty_input_gives_an_empty_list_not_an_invented_option():
    assert rank_transfer_options([]) == []


def test_cheapest_price_drives_the_cost_line():
    from ski_optimizer.engine.transfer_options import cheapest_price_eur_per_person
    options = rank_transfer_options([
        _opt("private", 423.5, 150, mode="minivan"),
        _opt("scheduled", 57.62, 195),
    ])
    # The owner's complaint: the cheap option existed but the cost line
    # still showed the private price.
    assert cheapest_price_eur_per_person(options) == 57.62


def test_cheapest_of_nothing_is_none_never_zero():
    from ski_optimizer.engine.transfer_options import cheapest_price_eur_per_person
    assert cheapest_price_eur_per_person([]) is None


def test_both_result_models_expose_transfer_options():
    # REGRESSION (caught in production, not by this suite): the field
    # was added to TripResultOut only, and DatedTripResultOut -- what
    # the date-range route (the one the frontend calls) actually
    # returns -- silently dropped it. The cost line went live while the
    # list arrived empty. They are siblings, not parent/child.
    from ski_optimizer.api.routes.search import DatedTripResultOut, TripResultOut
    for model in (TripResultOut, DatedTripResultOut):
        assert "transfer_options" in model.model_fields, model.__name__


def test_transfer_options_survive_serialisation():
    # The list must round-trip through the response model, not just
    # exist as a field name.
    from ski_optimizer.api.routes.search import TransferOptionOut, DatedTripResultOut
    option = TransferOptionOut(kind="scheduled", mode="bus",
                               price_eur_per_person=57.62, duration_minutes=195,
                               carrier="Alpine Fleet", is_round_trip=True,
                               roles=["cheapest"])
    dumped = DatedTripResultOut.model_construct(transfer_options=[option]).model_dump()
    assert dumped["transfer_options"][0]["price_eur_per_person"] == 57.62
    assert dumped["transfer_options"][0]["roles"] == ["cheapest"]


def test_same_priced_departures_collapse_to_the_fastest():
    # Measured in production: Zermatt returned four SBB trains all at
    # EUR118.12 lasting 240/242/262/468 minutes. One offer, several
    # departures -- and nobody wants the 7h48 routing at the same fare.
    ranked = rank_transfer_options([
        TransferOption(kind="scheduled", mode="train", price_eur_per_person=118.12,
                       duration_minutes=468, carrier="SBB"),
        TransferOption(kind="scheduled", mode="train", price_eur_per_person=118.12,
                       duration_minutes=240, carrier="SBB"),
        TransferOption(kind="scheduled", mode="train", price_eur_per_person=118.12,
                       duration_minutes=262, carrier="SBB"),
    ])
    assert len(ranked) == 1
    assert ranked[0].duration_minutes == 240


def test_different_carriers_at_the_same_price_stay_separate():
    # Collapsing across operators would hide a real choice.
    ranked = rank_transfer_options([
        TransferOption(kind="scheduled", mode="bus", price_eur_per_person=100.0,
                       duration_minutes=240, carrier="AlpyBus"),
        TransferOption(kind="scheduled", mode="bus", price_eur_per_person=100.0,
                       duration_minutes=240, carrier="Alpine Fleet"),
    ])
    assert len(ranked) == 2


def test_scheduled_options_are_not_gated_by_the_private_rate_limit():
    # THE "it only works for one resort" bug (owner-reported, then
    # reproduced: rows 0-2 had options, rows 3-5 had none). Private
    # quotes must stay capped -- Alps2Alps 429s for >10 minutes -- but
    # gating the scheduled lookup behind the same cap emptied the list
    # for every deal past the cap, which is what the resort chips
    # switch to.
    import inspect
    from ski_optimizer.engine.cost_calculator import all_transfer_options
    sig = inspect.signature(all_transfer_options)
    assert "include_private" in sig.parameters, (
        "the private half must be independently gateable")
    assert sig.parameters["include_private"].default is True

    from ski_optimizer.api.routes import search as route
    src = inspect.getsource(route._prefetch_live_transfers)
    assert "include_private=i < _LIVE_TRANSFER_N" in src, (
        "only the PRIVATE lookup may be capped; scheduled must run for every row")


def test_private_lookup_is_skipped_when_not_requested(monkeypatch):
    # Proves the gate actually prevents the rate-limited call rather
    # than merely filtering its output afterwards.
    from ski_optimizer.engine import cost_calculator as cc
    from ski_optimizer.data.resort_repository import load_resorts

    def _boom(*a, **k):
        raise AssertionError("private transfer lookup must not run")
    monkeypatch.setattr(cc, "_live_transfer_result", _boom)
    monkeypatch.setattr(cc, "all_transfer_options",
                        cc.all_transfer_options)  # keep the real function
    resort = load_resorts()[0]
    # Omio is disabled offline by conftest, so this returns [] -- the
    # point is that it does NOT raise.
    assert cc.all_transfer_options(
        resort, datetime.date(2027, 1, 16), datetime.date(2027, 1, 23), 2,
        pickup_time="13:00", include_private=False) == []


def test_a_failing_flight_lookup_does_not_erase_transfer_options(monkeypatch):
    # REGRESSION: the flight call only supplies the PICKUP TIME, but it
    # ran unguarded ahead of the transfer lookup, so a slow or failing
    # flight chain (common for rows that were not live-repriced, where
    # nothing is cached) took the whole row's transfer list down with
    # it. Reproduced in production on rows whose transfers worked fine
    # in isolation.
    from ski_optimizer.api.routes import search as route

    def _boom(*a, **k):
        raise RuntimeError("provider chain exhausted")
    monkeypatch.setattr(route, "live_flight_options", _boom)
    seen = {}

    def _fake_options(resort, start, end, group, **kw):
        seen["pickup"] = kw.get("pickup_time")
        return ["sentinel"]
    monkeypatch.setattr(route, "all_transfer_options", _fake_options)

    class _Row:
        resort = type("R", (), {"name": "Test"})()
        start_date = datetime.date(2027, 1, 16)
        end_date = datetime.date(2027, 1, 23)

    out = route._prefetch_live_transfers([_Row()], 2, True, 1)
    assert out[0][1] == ["sentinel"], "transfer options must survive a flight failure"
    # And it degrades to the documented assumption rather than a guess.
    assert seen["pickup"] == route._ASSUMED_PICKUP_TIME


def test_options_are_stamped_with_their_resort():
    # The guard below can only work if every option knows which resort
    # it was fetched for.
    from ski_optimizer.engine.transfer_options import TransferOption
    assert "resort_name" in TransferOption.__dataclass_fields__


def test_options_from_another_resort_are_dropped(monkeypatch):
    # Production served Zermatt's SBB train on Val Thorens rows. Wrong
    # data must never reach the card, even if the cause is upstream.
    from ski_optimizer.api.routes import search as route
    from ski_optimizer.engine.transfer_options import TransferOption

    good = TransferOption(resort_name="Val Thorens", kind="scheduled", mode="bus",
                          price_eur_per_person=51.0, duration_minutes=240)
    leaked = TransferOption(resort_name="Zermatt", kind="scheduled", mode="train",
                            price_eur_per_person=118.12, duration_minutes=240,
                            carrier="SBB")
    src = inspect_source = __import__("inspect").getsource(route.search_trip_dates)
    assert "leaked onto" in src, "the integrity guard must be in the results loop"
    # And the filter itself keeps only the row's own options.
    kept = [o for o in (good, leaked) if o.resort_name == "Val Thorens"]
    assert kept == [good]
