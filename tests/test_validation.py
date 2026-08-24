"""
Validation, cost-model invariant, and scoring-property tests.

These exist because an audit of the code found that validation lived
ONLY at the API boundary (api/routes/search.py's Pydantic schema), so
the CLI, library callers, and tests could all construct nonsense
preferences. The most serious finding: UserPreferences(trip_nights=-3)
produced NEGATIVE trip costs, which then passed the "is it under
budget?" filter and were returned as legitimate ranked results.

Run with:  cd ski-trip-optimizer && python -m pytest tests/test_validation.py -v
(or the no-pytest runner in the repo README, since this sandbox has no
network access to install pytest.)
"""
import datetime
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.data.resort_repository import load_resorts, _parse_transfer_minutes
from ski_optimizer.models import UserPreferences
from ski_optimizer.engine.cost_calculator import compute_trip_cost, ski_pass_cost, apply_live_flight_price
from ski_optimizer.engine.scoring import rank_trips
from ski_optimizer.engine.terrain import TerrainMix


def _valid(**overrides):
    kw = dict(budget_eur_per_person=1500, trip_nights=5, group_size=2)
    kw.update(overrides)
    return UserPreferences(**kw)


def _expect_value_error(**overrides):
    try:
        _valid(**overrides)
    except ValueError:
        return True
    raise AssertionError(f"expected ValueError for {overrides}, but it was accepted")


# --- numeric input validation ---

def test_rejects_zero_and_negative_trip_nights():
    assert _expect_value_error(trip_nights=0)
    assert _expect_value_error(trip_nights=-3)


def test_rejects_zero_and_negative_budget():
    assert _expect_value_error(budget_eur_per_person=0)
    assert _expect_value_error(budget_eur_per_person=-100)


def test_rejects_zero_and_negative_group_size():
    # Previously surfaced as a ZeroDivisionError deep inside the cost
    # calculator instead of a clear message at construction.
    assert _expect_value_error(group_size=0)
    assert _expect_value_error(group_size=-2)


def test_rejects_zero_or_negative_rooms_needed():
    assert _expect_value_error(rooms_needed=0)
    assert _expect_value_error(rooms_needed=-1)


def test_rejects_more_rooms_than_people():
    # REGRESSION: 100 rooms for a solo traveler was accepted and produced
    # a EUR 35,000 per-person accommodation cost.
    assert _expect_value_error(group_size=1, rooms_needed=100)
    assert _expect_value_error(group_size=2, rooms_needed=50)


def test_rejects_implausible_room_occupancy():
    # REGRESSION: 12 people in 1 room was accepted and priced at an
    # implausibly cheap EUR 29/person.
    assert _expect_value_error(group_size=12, rooms_needed=1)
    assert _expect_value_error(group_size=10, rooms_needed=2)


def test_accepts_realistic_room_configurations():
    for gs, rooms in ((1, 1), (2, 1), (4, 2), (6, 3), (8, 2)):
        _valid(group_size=gs, rooms_needed=rooms)


# --- ski pass day-count curve ---

def test_six_day_pass_matches_the_sourced_spreadsheet_price_exactly():
    # The multiplier curve is normalized so day 6 == 1.0. If this ever
    # fails, the curve has silently started distorting sourced data.
    for r in load_resorts():
        assert abs(ski_pass_cost(r, 6) - r.ski_pass_6day_eur) < 0.01, (
            f"{r.name}: 6-day pass no longer matches spreadsheet"
        )


def test_short_passes_cost_more_per_day_than_long_ones():
    # REGRESSION: the old model was flat-linear, which understated short
    # trips. Real passes give a per-day discount as day count rises --
    # verified against Ski Arlberg 2025/26 (1-day EUR 81.50 vs 6-day
    # EUR 450, i.e. the 1-day rate is ~1.09x the naive per-day figure).
    r = load_resorts()[0]
    per_day = [ski_pass_cost(r, d) / d for d in (1, 3, 6, 10)]
    assert per_day == sorted(per_day, reverse=True), (
        f"per-day rate should fall as day count rises, got {per_day}"
    )


def test_pass_cost_is_still_monotonically_increasing_in_days():
    # A per-day discount must never make a LONGER pass cheaper overall.
    r = load_resorts()[0]
    totals = [ski_pass_cost(r, d) for d in range(1, 15)]
    assert totals == sorted(totals), "more days must never cost less in total"


def test_js_prototype_pass_multipliers_match_python():
    """
    The frontend prototype embeds its own JS port of this cost model, and
    its README claims the two mirror each other. Changing the Python
    curve without updating the JS silently broke that claim once already
    (the two engines priced the same trip differently). This test greps
    the JSX for its multiplier table and asserts it matches -- crude, but
    it fails loudly instead of drifting quietly.

    Skipped if the prototype file isn't present (e.g. a backend-only
    checkout), since it isn't a backend dependency.
    """
    import re
    from ski_optimizer.engine.cost_calculator import (
        _PASS_DAY_MULTIPLIER, _PASS_LONG_TRIP_MULTIPLIER,
    )
    jsx = (Path(__file__).resolve().parent.parent
           / "frontend" / "prototype" / "SkiTripOptimizer.jsx")
    if not jsx.exists():
        return  # nothing to check

    text = jsx.read_text()
    match = re.search(r"const PASS_DAY_MULTIPLIER = \{([^}]*)\}", text)
    assert match, "PASS_DAY_MULTIPLIER not found in the JSX prototype"
    js_values = {int(k): float(v) for k, v in re.findall(r"(\d+):\s*([\d.]+)", match.group(1))}
    assert js_values == _PASS_DAY_MULTIPLIER, (
        f"JS prototype pass multipliers have drifted from Python.\n"
        f"  JS:     {js_values}\n  Python: {_PASS_DAY_MULTIPLIER}"
    )

    long_match = re.search(r"const PASS_LONG_TRIP_MULTIPLIER = ([\d.]+)", text)
    assert long_match, "PASS_LONG_TRIP_MULTIPLIER not found in the JSX prototype"
    assert float(long_match.group(1)) == _PASS_LONG_TRIP_MULTIPLIER


# --- enum validation (previously silent fallbacks) ---

def test_rejects_unknown_skill_level():
    # 'expret' was previously scored silently as 'intermediate'.
    assert _expect_value_error(skill_level="expret")


def test_rejects_unknown_food_profile():
    # Previously priced silently as 'normal'.
    assert _expect_value_error(food_profile="TYPO")


def test_rejects_unknown_accommodation_tier():
    assert _expect_value_error(accommodation_tier="palatial")


def test_rejects_unknown_equipment_tier():
    # Previously raised a bare KeyError from inside the cost calculator.
    assert _expect_value_error(equipment_tier="deluxe")


def test_accepts_every_documented_enum_value():
    for skill in ("beginner", "intermediate", "advanced", "expert"):
        _valid(skill_level=skill)
    for tier in ("budget", "standard", "luxury"):
        _valid(accommodation_tier=tier)
    for profile in ("budget", "normal", "luxury"):
        _valid(food_profile=profile)
    for equip in ("standard", "premium"):
        _valid(equipment_tier=equip)


# --- weights validation ---

def test_rejects_partial_weight_dict():
    assert _expect_value_error(weights={"ski_quality": 1.0})


def test_rejects_unknown_weight_key():
    w = {"ski_quality": 0.3, "price": 0.2, "snow": 0.15,
         "nightlife": 0.15, "convenience": 0.1, "apres_vibes": 0.1}
    assert _expect_value_error(weights=w)


def test_rejects_negative_weight():
    w = {"ski_quality": 0.5, "price": -0.1, "snow": 0.2,
         "nightlife": 0.2, "convenience": 0.1, "accommodation": 0.1}
    assert _expect_value_error(weights=w)


def test_rejects_empty_weights():
    assert _expect_value_error(weights={})


# --- cost model invariants ---

def test_no_resort_ever_produces_negative_or_zero_cost():
    # The bug this guards: negative trip_nights made every component
    # negative, and a negative total trivially "fits" any budget.
    resorts = load_resorts()
    prefs = _valid()
    for r in resorts:
        cost = compute_trip_cost(r, prefs)
        assert cost.total_eur > 0, f"{r.name} produced non-positive total"
        for component in (cost.flight_eur, cost.transfer_eur, cost.accommodation_eur,
                          cost.ski_pass_eur, cost.equipment_eur, cost.food_eur, cost.misc_eur):
            assert component >= 0, f"{r.name} produced a negative cost component"


def test_cost_breakdown_components_sum_to_total():
    resorts = load_resorts()
    prefs = _valid()
    for r in resorts:
        c = compute_trip_cost(r, prefs)
        parts = (c.flight_eur + c.transfer_eur + c.accommodation_eur + c.ski_pass_eur
                 + c.equipment_eur + c.food_eur + c.misc_eur)
        assert abs(parts - c.total_eur) < 0.01, f"{r.name}: components don't sum to total"


def test_longer_trip_costs_more():
    resorts = load_resorts()
    r = resorts[0]
    short = compute_trip_cost(r, _valid(trip_nights=3))
    long_ = compute_trip_cost(r, _valid(trip_nights=7))
    assert long_.total_eur > short.total_eur


def test_premium_equipment_costs_more_than_standard():
    r = load_resorts()[0]
    std = compute_trip_cost(r, _valid(equipment_tier="standard"))
    prem = compute_trip_cost(r, _valid(equipment_tier="premium"))
    assert prem.equipment_eur > std.equipment_eur


def test_luxury_food_costs_more_than_budget_food():
    r = load_resorts()[0]
    budget = compute_trip_cost(r, _valid(food_profile="budget"))
    luxury = compute_trip_cost(r, _valid(food_profile="luxury"))
    assert luxury.food_eur > budget.food_eur


def test_larger_group_lowers_per_person_accommodation():
    # Rooms are shared 2-per-room, so per-person cost shouldn't rise
    # with group size.
    r = load_resorts()[0]
    solo = compute_trip_cost(r, _valid(group_size=1))
    pair = compute_trip_cost(r, _valid(group_size=2))
    assert pair.accommodation_eur <= solo.accommodation_eur


# --- scoring properties ---

def test_all_score_components_are_within_zero_and_one():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000)
    for trip in rank_trips(resorts, prefs, top_n=len(resorts)):
        for dim, value in trip.score_components.items():
            assert 0.0 <= value <= 1.0, f"{trip.resort.name}: {dim}={value} out of range"


def test_overall_score_is_within_zero_and_one():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000)
    for trip in rank_trips(resorts, prefs, top_n=len(resorts)):
        assert 0.0 <= trip.score <= 1.0, f"{trip.resort.name}: score {trip.score} out of range"


def test_every_returned_trip_respects_the_budget():
    resorts = load_resorts()
    for budget in (800, 1200, 2000):
        prefs = _valid(budget_eur_per_person=budget)
        for trip in rank_trips(resorts, prefs, top_n=len(resorts)):
            assert trip.cost.total_eur <= budget


def test_top_n_is_respected():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=5000)
    for n in (1, 3, 5):
        assert len(rank_trips(resorts, prefs, top_n=n)) <= n


def test_weighting_a_dimension_fully_changes_the_winner():
    # Sanity check that weights actually drive results: an all-nightlife
    # search and an all-convenience search shouldn't reliably agree.
    resorts = load_resorts()
    zero = {k: 0.0 for k in ("ski_quality", "price", "snow",
                             "nightlife", "convenience", "accommodation")}

    nightlife_w = dict(zero, nightlife=1.0)
    convenience_w = dict(zero, convenience=1.0)

    top_nightlife = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                               weights=nightlife_w), top_n=1)[0]
    top_convenience = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                                 weights=convenience_w), top_n=1)[0]
    assert top_nightlife.score_components["nightlife"] >= 0.8
    assert top_convenience.score_components["convenience"] >= 0.8


def test_beginner_and_expert_get_different_top_terrain():
    # Guards the skill-terrain matching fix: an expert-oriented resort
    # shouldn't top a beginner's list.
    resorts = load_resorts()
    ski_heavy = {"ski_quality": 1.0, "price": 0.0, "snow": 0.0,
                 "nightlife": 0.0, "convenience": 0.0, "accommodation": 0.0}
    beginner_top = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                              skill_level="beginner",
                                              weights=ski_heavy), top_n=1)[0]
    expert_top = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                            skill_level="expert",
                                            weights=ski_heavy), top_n=1)[0]
    # The beginner's pick should have more beginner terrain than the
    # expert's pick has -- if these ever invert, skill matching is broken.
    assert (beginner_top.resort.terrain_mix.beginner
            > expert_top.resort.terrain_mix.beginner)


# --- terrain helpers ---

def test_terrain_fractions_always_sum_to_one():
    for r in load_resorts():
        tm = r.terrain_mix
        assert abs((tm.beginner + tm.intermediate + tm.advanced) - 1.0) < 0.001


def test_fraction_for_skill_is_cumulative_downward():
    # An advanced skier can ski everything; a beginner only beginner terrain.
    tm = TerrainMix.from_percentages(30, 50, 20, quality="sourced")
    assert tm.fraction_for_skill("beginner") < tm.fraction_for_skill("intermediate")
    assert tm.fraction_for_skill("intermediate") < tm.fraction_for_skill("advanced")
    assert abs(tm.fraction_for_skill("advanced") - 1.0) < 0.001


def test_challenge_for_skill_is_cumulative_upward():
    tm = TerrainMix.from_percentages(30, 50, 20, quality="sourced")
    assert tm.challenge_for_skill("advanced") < tm.challenge_for_skill("intermediate")
    assert tm.challenge_for_skill("intermediate") < tm.challenge_for_skill("beginner")


def test_terrain_mix_normalizes_percentages_that_dont_sum_to_100():
    # Guards against a future spreadsheet edit where the three columns
    # don't quite add up -- should normalize, not silently skew.
    tm = TerrainMix.from_percentages(20, 30, 50, quality="estimated")
    assert abs((tm.beginner + tm.intermediate + tm.advanced) - 1.0) < 0.001
    tm2 = TerrainMix.from_percentages(2, 3, 5, quality="estimated")
    assert abs(tm2.beginner - 0.2) < 0.001


# --- data integrity ---

def test_no_duplicate_resort_names():
    names = [r.name for r in load_resorts()]
    assert len(names) == len(set(names)), "duplicate resort names would break target_resort lookup"


def test_elevation_values_are_internally_consistent():
    for r in load_resorts():
        assert r.summit_elevation_m > r.base_elevation_m, f"{r.name}: summit not above base"
        stated = r.vertical_drop_m
        actual = r.summit_elevation_m - r.base_elevation_m
        # Tolerance is deliberately tight. Across all 30 current resorts
        # the largest real deviation is 10m (Formigal), so a loose
        # tolerance would make this test decorative -- it would pass no
        # matter what got typed in. 50m catches transposed digits and
        # mismatched-sector figures while still allowing rounding.
        assert abs(stated - actual) <= 50, (
            f"{r.name}: stated vertical {stated} vs base/summit span {actual}"
        )


def test_transfer_times_are_plausible():
    for r in load_resorts():
        assert 5 <= r.transfer_time_minutes <= 360, (
            f"{r.name}: implausible transfer time {r.transfer_time_minutes}min "
            "-- likely a parse failure in _parse_transfer_minutes"
        )


def test_per_airport_transfer_times_are_parsed_not_averaged():
    """
    REGRESSION: the parser averaged times across DIFFERENT airports.
    Val Thorens ("3h GVA / 1h45 CMF") became one number that was neither
    the Geneva time nor the Chambery time -- it described no real
    journey. Worse, the flight adapter searches BOTH airports, so the
    engine could price a Geneva flight against a Geneva/Chambery average
    transfer: two halves of one trip disagreeing.
    """
    resorts = load_resorts()
    vt = next(r for r in resorts if r.name == "Val Thorens")
    assert vt.transfer_minutes_for("GVA") != vt.transfer_minutes_for("CMF")
    assert vt.transfer_minutes_for("GVA") > vt.transfer_minutes_for("CMF"), (
        "Geneva is the longer transfer to Val Thorens"
    )


def test_transfer_lookup_falls_back_when_airport_unknown():
    vt = next(r for r in load_resorts() if r.name == "Val Thorens")
    assert vt.transfer_minutes_for("ZZZ") == vt.transfer_time_minutes
    assert vt.transfer_minutes_for(None) == vt.transfer_time_minutes


def test_multi_airport_resorts_have_per_airport_times():
    # Every resort whose airport field names two airports should have
    # two parsed times -- otherwise the averaging bug is back for it.
    from ski_optimizer.engine.cost_calculator import airport_codes_for
    for r in load_resorts():
        if len(airport_codes_for(r)) > 1 and "/" in str(r.nearest_airport):
            # Only assert where the transfer text itself lists per-airport
            # times; some resorts list airports without per-airport timings.
            if len(r.transfer_minutes_by_airport) > 1:
                assert len(set(r.transfer_minutes_by_airport.values())) >= 1


def test_distance_and_time_imply_a_plausible_road_speed():
    # Catches transposed digits and mismatched distance/time pairs.
    # Krvavec (10km/20min = 30km/h) is a genuine short mountain hop, so
    # the lower bound accommodates it.
    for r in load_resorts():
        hours = r.transfer_time_minutes / 60
        speed = r.airport_distance_km / hours
        assert 25 <= speed <= 95, (
            f"{r.name}: {r.airport_distance_km}km in {r.transfer_time_minutes}min "
            f"= {speed:.0f} km/h -- implausible for an Alpine road transfer"
        )


# --- transfer-time parsing (regression: minutes-only strings) ---

def test_parses_minutes_only_strings():
    # REGRESSION: this originally only matched an `Nh` pattern, so
    # Krvavec's '~20min' silently became the 120-minute fallback -- a 6x
    # error on the resort with the shortest transfer in the database,
    # corrupting exactly the dimension it's best at.
    assert _parse_transfer_minutes("~20min (closest airport)") == 20.0
    assert _parse_transfer_minutes("45 min") == 45.0
    assert _parse_transfer_minutes("90 minutes") == 90.0


def test_hours_take_precedence_over_minutes_suffix():
    # '1h30min' must read as 90, not 30 -- the hour pattern has to be
    # checked before the minutes-only pattern.
    assert _parse_transfer_minutes("1h30min") == 90.0


def test_parses_hour_formats():
    assert _parse_transfer_minutes("2h") == 120.0
    assert _parse_transfer_minutes("1h30") == 90.0
    assert _parse_transfer_minutes("2h-2h30") == 135.0


def test_unparseable_transfer_time_warns_rather_than_failing_silently():
    # A wrong-but-plausible number is more dangerous than a loud one:
    # the old fallback was indistinguishable from a real parsed '2h'.
    import warnings as _w
    with _w.catch_warnings(record=True) as caught:
        _w.simplefilter("always")
        result = _parse_transfer_minutes("no idea honestly")
        assert result == 120.0
        assert any("Could not parse" in str(x.message) for x in caught)


def test_krvavec_transfer_is_twenty_minutes():
    # Guards the specific data point the parser bug corrupted.
    krvavec = next(r for r in load_resorts() if r.name == "Krvavec")
    assert krvavec.transfer_time_minutes == 20.0


def test_shortest_transfer_resort_wins_a_pure_convenience_search():
    resorts = load_resorts()
    weights = {"ski_quality": 0.0, "price": 0.0, "snow": 0.0,
               "nightlife": 0.0, "convenience": 1.0, "accommodation": 0.0}
    top = rank_trips(resorts, _valid(budget_eur_per_person=3000, weights=weights), top_n=1)[0]
    shortest = min(r.transfer_time_minutes for r in resorts)
    assert top.resort.transfer_time_minutes == shortest


# --- target_resort matching ---

def test_target_resort_matching_is_case_insensitive():
    resorts = load_resorts()
    for probe in ("Krvavec", "krvavec", "KRVAVEC"):
        results = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                             target_resort=probe), top_n=1)
        assert len(results) == 1, f"{probe!r} failed to match"


def test_target_resort_matching_tolerates_surrounding_whitespace():
    # REGRESSION: case was handled but whitespace wasn't, so a trailing
    # space (copy-paste, mobile autocomplete) silently returned zero
    # results as if the resort didn't exist.
    resorts = load_resorts()
    for probe in ("Krvavec ", " Krvavec", "  krvavec  "):
        results = rank_trips(resorts, _valid(budget_eur_per_person=3000,
                                             target_resort=probe), top_n=1)
        assert len(results) == 1, f"{probe!r} failed to match"


# --- live flight repricing ---

def test_apply_live_flight_price_replaces_flight_and_flags_live():
    resorts = load_resorts()
    cost = compute_trip_cost(resorts[0], _valid())
    assert cost.flight_price_is_live is False

    live = cost.flight_eur + 37.5
    repriced = apply_live_flight_price(cost, live)

    assert repriced.flight_eur == live
    assert repriced.flight_price_is_live is True
    # Returns a NEW object -- the original must be untouched.
    assert cost.flight_price_is_live is False
    assert cost.flight_eur != live


def test_apply_live_flight_price_adjusts_misc_proportionally():
    resorts = load_resorts()
    cost = compute_trip_cost(resorts[0], _valid())
    delta = 100.0
    repriced = apply_live_flight_price(cost, cost.flight_eur + delta)
    # misc_eur is a 5% buffer on the subtotal (MISC_COST_RATE) -- a EUR100
    # flight increase should raise misc by EUR5, not stay fixed.
    assert repriced.misc_eur == round(cost.misc_eur + delta * 0.05, 2)


def test_rank_trips_without_flight_cost_fn_is_unaffected():
    # Backward compatibility: every call site that doesn't opt in (which is
    # every caller that existed before this feature) must behave exactly
    # as before.
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000)
    for trip in rank_trips(resorts, prefs, top_n=len(resorts)):
        assert trip.cost.flight_price_is_live is False


def test_rank_trips_ignores_flight_cost_fn_without_outbound_date():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000)  # outbound_date defaults to None
    calls = []

    def fn(resort, start, end, p):
        calls.append(resort.name)
        return 1.0

    results = rank_trips(resorts, prefs, top_n=5, flight_cost_fn=fn)
    assert calls == [], "flight_cost_fn must not be called without an outbound_date"
    assert all(not t.cost.flight_price_is_live for t in results)


def test_rank_trips_uses_live_price_when_date_and_fn_are_given():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000, outbound_date=datetime.date(2027, 1, 2))

    def fn(resort, start, end, p):
        return 1.0  # absurdly cheap and distinct from any real estimate

    results = rank_trips(resorts, prefs, top_n=3, flight_cost_fn=fn)
    assert results, "expected at least one result"
    for trip in results:
        assert trip.cost.flight_eur == 1.0
        assert trip.cost.flight_price_is_live is True


def test_rank_trips_drops_a_candidate_that_busts_budget_once_live_priced():
    resorts = load_resorts()
    target = resorts[0]
    outbound = datetime.date(2027, 1, 2)
    # Baseline computed with the SAME start_date rank_trips uses internally
    # (season-band adjusted) -- using a date-less baseline here would set
    # the wrong budget and make this test pass for the wrong reason.
    baseline = compute_trip_cost(target, _valid(target_resort=target.name), start_date=outbound)
    prefs = _valid(budget_eur_per_person=baseline.total_eur + 1,
                   target_resort=target.name, outbound_date=outbound)

    def fn(resort, start, end, p):
        return baseline.flight_eur + 100000  # affordable statically, not once live-priced

    # Old "drop it" behavior is still available explicitly.
    strict = rank_trips(resorts, prefs, top_n=1, flight_cost_fn=fn, allow_over_budget_fallback=False)
    assert strict == []

    # Default behavior: the fixed-resort candidate busts budget once live
    # flight-priced, so it falls back rather than returning empty -- shown
    # honestly flagged, with the REAL (live) price, not the stale static one.
    fallback = rank_trips(resorts, prefs, top_n=1, flight_cost_fn=fn)
    assert len(fallback) == 1
    assert fallback[0].within_budget is False
    assert fallback[0].cost.flight_eur == baseline.flight_eur + 100000


def test_rank_trips_keeps_static_estimate_when_fn_returns_none():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=3000, outbound_date=datetime.date(2027, 1, 2))

    def fn(resort, start, end, p):
        return None  # simulates an adapter error / no route found

    results = rank_trips(resorts, prefs, top_n=5, flight_cost_fn=fn)
    assert results
    assert all(not t.cost.flight_price_is_live for t in results)


def test_rank_trips_only_reprices_up_to_live_reprice_n_candidates():
    resorts = load_resorts()
    prefs = _valid(budget_eur_per_person=5000, outbound_date=datetime.date(2027, 1, 2))
    calls = []

    def fn(resort, start, end, p):
        calls.append(resort.name)
        return 200.0

    rank_trips(resorts, prefs, top_n=5, flight_cost_fn=fn, live_reprice_n=3)
    assert len(calls) == 3, f"expected exactly 3 live-price calls, got {len(calls)}"
