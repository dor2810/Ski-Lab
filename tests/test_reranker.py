"""
Tests for engine/reranker.py -- blueprint Milestone 5 (re-rank a trip
set when snow conditions change). Pure/offline: weather_fn is injected,
so nothing here touches the network.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.models import (
    Resort, TripOption, CostBreakdown, DailyWeather, TripWeatherSummary,
)
from ski_optimizer.engine.reranker import (
    rerank_with_conditions, snow_depth_score, blended_snow_score,
    live_forecast_confidence, MAX_LIVE_WEIGHT,
)
from ski_optimizer.data.resort_repository import load_resorts

WEIGHTS = {"ski_quality": 0.3, "price": 0.2, "snow": 0.15,
           "nightlife": 0.15, "convenience": 0.1, "accommodation": 0.1}


def _resort(name):
    return next(r for r in load_resorts() if r.name == name)


def _cost():
    return CostBreakdown(flight_eur=200, transfer_eur=50, accommodation_eur=300,
                         ski_pass_eur=300, equipment_eur=100, food_eur=200, misc_eur=50)


def _trip(name, score, snow):
    return TripOption(resort=_resort(name), cost=_cost(), score=score,
                      score_components={"ski_quality": 0.5, "price": 0.5, "snow": snow,
                                        "nightlife": 0.5, "convenience": 0.5,
                                        "accommodation": 0.5})


def _summary(depth_cm, live_days, total_days=6):
    days = [
        DailyWeather(date=None, is_live_forecast=(i < live_days), temp_max_c=-2,
                     temp_min_c=-8, snowfall_cm=1.0, snow_depth_cm=depth_cm,
                     description=None, years_sampled=None)
        for i in range(total_days)
    ]
    return TripWeatherSummary(days=days, avg_temp_max_c=-2, avg_temp_min_c=-8,
                              avg_snowfall_cm=1.0, avg_snow_depth_cm=depth_cm)


# --- the depth curve ---

def test_snow_depth_score_rises_monotonically_with_depth():
    depths = [0, 10, 20, 40, 60, 80, 120, 170, 250]
    scores = [snow_depth_score(d) for d in depths]
    assert scores == sorted(scores), f"deeper snow must never score worse: {scores}"


def test_deep_base_scores_far_above_bare_ground():
    assert snow_depth_score(220) > 0.9
    assert snow_depth_score(5) < 0.15


# --- confidence gating ---

def test_far_future_trip_is_left_completely_unchanged():
    # Every day historical -> confidence 0 -> the historical record IS
    # the better signal and snow_reliability already encodes it.
    summary = _summary(depth_cm=250, live_days=0)
    assert live_forecast_confidence(summary) == 0.0
    assert blended_snow_score(0.4, summary) == 0.4


def test_fully_forecast_trip_moves_by_at_most_the_capped_weight():
    summary = _summary(depth_cm=250, live_days=6)
    assert live_forecast_confidence(summary) == 1.0
    blended = blended_snow_score(0.0, summary)
    # A perfect live score against a zero static score can only pull the
    # result up to MAX_LIVE_WEIGHT, never to 1.0.
    assert abs(blended - MAX_LIVE_WEIGHT * snow_depth_score(250)) < 1e-9
    assert blended <= MAX_LIVE_WEIGHT


def test_partial_forecast_moves_proportionally_less_than_full():
    deep = 250
    half = blended_snow_score(0.2, _summary(deep, live_days=3))
    full = blended_snow_score(0.2, _summary(deep, live_days=6))
    assert 0.2 < half < full


# --- re-ranking behaviour ---

def test_great_snow_promotes_a_trip_above_a_higher_ranked_one():
    # REGRESSION this exists to prevent: before the reranker was built,
    # a resort with a strong historical reputation and no snow this week
    # still outranked a lesser resort sitting on a deep base.
    trips = [_trip("Zermatt", 0.700, 0.90), _trip("Livigno", 0.660, 0.30)]
    depths = {"Zermatt": 20, "Livigno": 240}
    out = rerank_with_conditions(
        trips, WEIGHTS,
        weather_fn=lambda r: _summary(depths[r.name], live_days=6))
    assert [t.resort.name for t in out] == ["Livigno", "Zermatt"]


def test_a_failed_lookup_keeps_the_trip_at_its_original_score():
    trips = [_trip("Zermatt", 0.70, 0.9), _trip("Livigno", 0.66, 0.3)]
    out = rerank_with_conditions(trips, WEIGHTS, weather_fn=lambda r: None)
    assert [t.score for t in out] == [0.70, 0.66]
    assert [t.resort.name for t in out] == ["Zermatt", "Livigno"]


def test_lookups_are_bounded_to_avoid_request_amplification():
    # Each lookup is several real live requests; re-ranking a whole
    # result set would multiply them across every resort.
    names = ["Zermatt", "Livigno", "Chamonix", "Verbier", "Ischgl", "Bansko", "Sölden"]
    trips = [_trip(n, 0.7 - i * 0.01, 0.5) for i, n in enumerate(names)]
    calls = []

    def weather_fn(resort):
        calls.append(resort.name)
        return _summary(240, live_days=6)

    rerank_with_conditions(trips, WEIGHTS, weather_fn=weather_fn, max_lookups=3)
    assert len(calls) == 3


def test_zero_snow_weight_spends_no_requests_at_all():
    calls = []
    trips = [_trip("Zermatt", 0.7, 0.9)]
    weights = dict(WEIGHTS, snow=0.0)
    rerank_with_conditions(trips, weights,
                           weather_fn=lambda r: calls.append(r.name) or _summary(240, 6))
    assert calls == []


def test_input_list_is_never_mutated():
    trips = [_trip("Zermatt", 0.70, 0.90), _trip("Livigno", 0.66, 0.30)]
    before_scores = [t.score for t in trips]
    before_order = [t.resort.name for t in trips]
    rerank_with_conditions(trips, WEIGHTS, weather_fn=lambda r: _summary(240, live_days=6))
    assert [t.score for t in trips] == before_scores
    assert [t.resort.name for t in trips] == before_order
