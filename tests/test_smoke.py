"""
Basic sanity checks, not a full test suite. Run with:
    cd ski-trip-optimizer && python -m pytest tests/ -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.data.resort_repository import load_resorts
from ski_optimizer.models import UserPreferences
from ski_optimizer.engine.scoring import rank_trips
from ski_optimizer.engine.cost_calculator import compute_trip_cost
from ski_optimizer.engine.terrain import parse_terrain_mix


def test_load_resorts_returns_all_resorts():
    resorts = load_resorts()
    assert len(resorts) == 37


def test_all_resorts_have_positive_core_fields():
    for r in load_resorts():
        assert r.piste_km > 0
        assert r.ski_pass_6day_eur > 0
        assert r.accommodation_eur_per_night > 0
        assert 1 <= r.off_piste_rating <= 5
        assert 1 <= r.snow_reliability <= 5


def test_cost_breakdown_totals_are_positive():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=2000, ski_days=5, group_size=2)
    for r in resorts:
        cost = compute_trip_cost(r, prefs)
        assert cost.total_eur > 0


def test_hard_budget_constraint_is_enforced():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=50, ski_days=5, group_size=2)
    # No resort fits a 50 EUR/person budget -- rank_trips no longer returns
    # an empty list for this (see its over-budget-fallback docstring), it
    # returns the cheapest option(s) it found, honestly flagged as not
    # fitting. The constraint is still enforced: nothing claims to fit.
    results = rank_trips(resorts, prefs)
    assert results
    assert all(not t.within_budget for t in results)

    # The old "empty means nothing fits" behavior is still available
    # explicitly, for a caller that wants it.
    strict_results = rank_trips(resorts, prefs, allow_over_budget_fallback=False)
    assert strict_results == []


def test_ranking_is_sorted_descending_by_score():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=2000, ski_days=5, group_size=2)
    results = rank_trips(resorts, prefs, top_n=10)
    scores = [t.score for t in results]
    assert scores == sorted(scores, reverse=True)


def test_weights_must_sum_to_one():
    try:
        UserPreferences(budget_eur_per_person=1000, ski_days=5,
                         weights={"ski_quality": 0.5, "price": 0.2})
        assert False, "should have raised"
    except ValueError:
        pass


def test_target_resort_mode_returns_only_that_resort():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=2000, ski_days=5,
                             group_size=2, target_resort="Livigno")
    results = rank_trips(resorts, prefs)
    assert len(results) == 1
    assert results[0].resort.name == "Livigno"


def test_target_resort_not_found_returns_empty():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=2000, ski_days=5,
                             group_size=2, target_resort="Nonexistent Resort")
    results = rank_trips(resorts, prefs)
    assert results == []


def test_include_resorts_restricts_to_exactly_those():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=3000, ski_days=5, group_size=2,
                            include_resorts=["Livigno", "Bansko"])
    results = rank_trips(resorts, prefs, top_n=10)
    names = {t.resort.name for t in results}
    assert names <= {"Livigno", "Bansko"}
    assert len(results) == 2  # both affordable at this budget


def test_exclude_resorts_removes_just_those():
    resorts = load_resorts()
    prefs = UserPreferences(budget_eur_per_person=3000, ski_days=5, group_size=2,
                            exclude_resorts=["Val Thorens"])
    results = rank_trips(resorts, prefs, top_n=100)
    names = {t.resort.name for t in results}
    assert "Val Thorens" not in names
    assert len(names) > 1  # everything else is still in play


def test_include_resorts_score_normalization_uses_full_dataset():
    # A 2-resort pin must NOT collapse the price-score normalization
    # range down to just those 2 resorts -- that would make 'price'
    # meaningless (always 0 or 1). Compare against the same resort
    # pinned alone via target_resort, which already uses the full range.
    resorts = load_resorts()
    via_target = rank_trips(resorts, UserPreferences(
        budget_eur_per_person=3000, ski_days=5, group_size=2, target_resort="Livigno"))
    via_include = rank_trips(resorts, UserPreferences(
        budget_eur_per_person=3000, ski_days=5, group_size=2, include_resorts=["Livigno"]))
    assert via_target[0].score_components["price"] == via_include[0].score_components["price"]


# --- terrain parser tests ---

def test_terrain_parses_clean_percentages():
    m = parse_terrain_mix("40% Beg, 40% Int, 20% Adv")
    assert m is not None
    assert abs(m.beginner - 0.40) < 0.01
    assert abs(m.intermediate - 0.40) < 0.01
    assert abs(m.advanced - 0.20) < 0.01


def test_terrain_parses_hyphenated_band():
    m = parse_terrain_mix("23% Beg, 31% Int, 46% Adv-Exp")
    assert m is not None
    assert abs(m.advanced - 0.46) < 0.01


def test_terrain_parses_run_counts():
    m = parse_terrain_mix("8 green, 36 blue, 23 red, 9 black (Méribel sector)")
    assert m is not None
    assert m.source == "run_counts"
    # 44 beginner-graded (green+blue) out of 76 total
    assert abs(m.beginner - 44 / 76) < 0.01


def test_terrain_returns_none_for_purely_qualitative_text():
    m = parse_terrain_mix("mixed, strong Int-Adv, some Beg (Sunnegga/Riffelberg)")
    assert m is None


def test_terrain_returns_none_for_empty_text():
    assert parse_terrain_mix("") is None
    assert parse_terrain_mix(None) is None


def test_terrain_mix_fractions_sum_to_one():
    m = parse_terrain_mix("57% Beg-Int (blue), 33% Int (red), 10% Adv (black)")
    assert m is not None
    assert abs((m.beginner + m.intermediate + m.advanced) - 1.0) < 0.01


def test_all_resorts_now_have_terrain_data():
    # Post-migration: every resort has a real or clearly-flagged-estimated
    # numeric terrain split -- unlike the old free-text parser, nothing
    # should fall through to None anymore.
    for r in load_resorts():
        assert r.terrain_mix is not None, f"{r.name} has no terrain_mix"
        assert r.terrain_data_quality in ("sourced", "sourced_conflicting", "estimated")


def test_zermatt_is_flagged_sourced_conflicting():
    resorts = load_resorts()
    zermatt = next(r for r in resorts if r.name == "Zermatt")
    assert zermatt.terrain_data_quality == "sourced_conflicting"
    assert zermatt.terrain_mix is not None


# --- extended data (snowfall/glacier/season/park/flight access) ---

def test_all_resorts_have_extended_data():
    for r in load_resorts():
        assert r.avg_annual_snowfall_cm is not None, f"{r.name} missing snowfall"
        assert r.glacier_access, f"{r.name} missing glacier_access"
        assert r.typical_season, f"{r.name} missing typical_season"
        assert r.terrain_park, f"{r.name} missing terrain_park"
        assert r.israeli_flight_access, f"{r.name} missing israeli_flight_access"
        assert r.extended_data_quality in ("sourced", "sourced_conflicting", "mixed", "estimated")


def test_zermatt_has_glacier_access():
    resorts = load_resorts()
    zermatt = next(r for r in resorts if r.name == "Zermatt")
    assert "Yes" in zermatt.glacier_access


def test_val_thorens_is_not_glacial():
    # Highest non-glacier base in the Alps -- a common point of
    # confusion given its altitude, worth a regression test.
    resorts = load_resorts()
    vt = next(r for r in resorts if r.name == "Val Thorens")
    assert vt.glacier_access.startswith("No")


def test_ischgl_flags_conflicting_snowfall_sources():
    resorts = load_resorts()
    ischgl = next(r for r in resorts if r.name == "Ischgl")
    assert ischgl.extended_data_quality == "sourced_conflicting"


def test_missing_terrain_data_does_not_crash_scoring():
    # Historically Zermatt had no parseable terrain text and stood in for
    # this scenario; it's since been researched (see
    # test_zermatt_is_flagged_sourced_conflicting) and no resort in the
    # current dataset has a None terrain_mix anymore (see
    # test_all_resorts_now_have_terrain_data) -- so relying on the real
    # catalog to exercise this path stopped testing anything. scoring.py
    # still has an explicit `if resort.terrain_mix is None` branch
    # (engine/scoring.py's _ski_quality_score), so test it directly with
    # a synthetic resort instead of hoping the real data exhibits the gap.
    import dataclasses
    resorts = load_resorts()
    mutated = [dataclasses.replace(r, terrain_mix=None) if r.name == "Zermatt" else r
               for r in resorts]
    prefs = UserPreferences(budget_eur_per_person=2000, ski_days=5,
                             group_size=2, skill_level="beginner")
    results = rank_trips(mutated, prefs, top_n=len(mutated))
    names = {t.resort.name for t in results}
    assert names == {r.name for r in resorts}
