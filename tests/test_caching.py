"""
Tests for the two caching layers.

Both run fully offline: the response cache is pure in-memory logic, and
fare persistence runs against an in-memory SQLite via SQLAlchemy.

NOTE: the fare-history half needs sqlalchemy installed. Where it isn't
available (as in the sandbox this was written in), those tests skip
themselves rather than failing -- see _SQLALCHEMY_AVAILABLE. The
response-cache half has no dependencies and always runs.
"""
import sys
import time
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.adapters.response_cache import MemoryResponseCache
from ski_optimizer.models import FlightOption, FlightSearchResult, PriceInsight

try:
    import sqlalchemy  # noqa: F401
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    _SQLALCHEMY_AVAILABLE = False


class SkippedTest(Exception):
    """
    Raised instead of returning early, so a skipped test is REPORTED as
    skipped rather than silently counted as a pass.

    This matters: the first version of this file just `return`ed when
    sqlalchemy was missing, and the runner dutifully printed PASS for
    eight tests that had executed nothing. A test that cannot fail is
    decorative, and one that reports success without running is worse.
    """


def _require_sqlalchemy():
    if not _SQLALCHEMY_AVAILABLE:
        raise SkippedTest("sqlalchemy not installed")


# ===========================================================================
# Response cache -- the ephemeral layer
# ===========================================================================

def test_stores_and_retrieves_a_value():
    cache = MemoryResponseCache()
    cache.set("k", "v")
    assert cache.get("k") == "v"


def test_missing_key_returns_none():
    assert MemoryResponseCache().get("nope") is None


def test_entry_expires_after_ttl():
    cache = MemoryResponseCache(ttl_seconds=1)
    cache.set("k", "v")
    assert cache.get("k") == "v"
    time.sleep(1.05)
    assert cache.get("k") is None


def test_cache_is_bounded_and_evicts_oldest():
    # THE BUG THIS FIXES: the original implementation only checked TTL
    # on read, so entries never read again stayed forever. Verified at
    # the time: 500 stale inserts left 500 entries, all expired, none
    # evicted -- a slow leak in a long-running server.
    cache = MemoryResponseCache(max_entries=10)
    for i in range(100):
        cache.set(f"key-{i}", i)
    assert len(cache) == 10, f"cache grew past its bound: {len(cache)} entries"


def test_eviction_is_least_recently_used_not_insertion_order():
    cache = MemoryResponseCache(max_entries=3)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    cache.get("a")          # 'a' is now the most recently used
    cache.set("d", 4)       # forces one eviction
    assert cache.get("a") == 1, "recently-used entry was wrongly evicted"
    assert cache.get("b") is None, "least-recently-used entry should have gone"


def test_expired_entries_are_pruned_on_write():
    # Guards the exact leak above from the other direction: entries that
    # are never READ again must still get cleaned up.
    cache = MemoryResponseCache(max_entries=1000, ttl_seconds=1)
    for i in range(50):
        cache.set(f"stale-{i}", i)
    assert len(cache) == 50
    time.sleep(1.05)
    cache.set("fresh", "x")   # triggers a prune
    assert len(cache) == 1, f"expired entries were not pruned: {len(cache)} left"


def test_overwriting_a_key_does_not_duplicate_it():
    cache = MemoryResponseCache()
    cache.set("k", "first")
    cache.set("k", "second")
    assert len(cache) == 1
    assert cache.get("k") == "second"


def test_clear_empties_the_cache_and_resets_stats():
    cache = MemoryResponseCache()
    cache.set("k", "v")
    cache.get("k")
    cache.clear()
    assert len(cache) == 0
    assert cache.stats()["hits"] == 0


def test_stats_track_hit_rate():
    # A low hit rate means we're burning paid API quota -- worth being
    # able to observe.
    cache = MemoryResponseCache()
    cache.set("k", "v")
    cache.get("k")      # hit
    cache.get("k")      # hit
    cache.get("miss")   # miss
    stats = cache.stats()
    assert stats["hits"] == 2 and stats["misses"] == 1
    assert abs(stats["hit_rate"] - (2 / 3)) < 0.001


def test_rejects_nonsensical_configuration():
    for kwargs in ({"max_entries": 0}, {"max_entries": -5}, {"ttl_seconds": 0}):
        try:
            MemoryResponseCache(**kwargs)
            assert False, f"expected ValueError for {kwargs}"
        except ValueError:
            pass


def test_concurrent_writes_do_not_corrupt_the_cache():
    # FastAPI serves sync routes from a threadpool, so concurrent
    # searches really can hit this simultaneously.
    import threading
    cache = MemoryResponseCache(max_entries=200)
    errors = []

    def worker(offset):
        try:
            for i in range(200):
                cache.set(f"k-{offset}-{i}", i)
                cache.get(f"k-{offset}-{i}")
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not errors, f"concurrent access raised: {errors}"
    assert len(cache) <= 200


def test_cache_backend_is_swappable():
    # The Redis migration path: implement the same three methods, swap
    # in via set_cache(), and adapters/ needs no changes.
    from ski_optimizer.adapters import response_cache

    class FakeCache(response_cache.ResponseCache):
        def __init__(self):
            self.store = {}
        def get(self, key):
            return self.store.get(key)
        def set(self, key, value):
            self.store[key] = value
        def clear(self):
            self.store.clear()

    original = response_cache.get_cache()
    try:
        fake = FakeCache()
        response_cache.set_cache(fake)
        response_cache.get_cache().set("k", "v")
        assert fake.store["k"] == "v"
    finally:
        response_cache.set_cache(original)


# ===========================================================================
# Fare history -- the durable layer
# ===========================================================================

def _session():
    """In-memory SQLite session with the fare tables created."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool
    from ski_optimizer.db.database import Base
    from ski_optimizer.db import fare_history  # noqa: F401 -- registers tables

    engine = create_engine("sqlite:///:memory:",
                           connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _sample_result():
    return FlightSearchResult(
        options=[
            FlightOption(price_eur=167, origin_airport="TLV",
                         destination_airport="GVA", airline="Wizz Air",
                         total_duration_minutes=275, stops=0),
            FlightOption(price_eur=214, origin_airport="TLV",
                         destination_airport="GVA", airline="easyJet",
                         total_duration_minutes=275, stops=0),
        ],
        insight=PriceInsight(
            lowest_price_eur=167,
            typical_range_eur=(210.0, 340.0),
            price_level="low",
            price_history=[[1766448000, 245], [1766534400, 238], [1766620800, 167]],
        ),
    )


def test_records_each_flight_option_as_an_observation():
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import record_search_result, FareObservation
    db = _session()
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), _sample_result())
    db.commit()
    assert db.query(FareObservation).count() == 2


def test_provider_history_is_stored_separately_from_our_observations():
    # The honesty rule: a price the provider REPORTS is not a price we
    # OBSERVED. Conflating them would let unverified data pass as our own.
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import (
        record_search_result, FareObservation, FareHistoryPoint,
    )
    db = _session()
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), _sample_result())
    db.commit()
    assert db.query(FareObservation).count() == 2
    assert db.query(FareHistoryPoint).count() == 3


def test_history_points_are_deduplicated_on_replay():
    # Re-running the same search must not inflate the record.
    _require_sqlalchemy()
    from sqlalchemy.exc import IntegrityError
    from ski_optimizer.db.fare_history import record_search_result, FareHistoryPoint
    db = _session()
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), _sample_result())
    db.commit()
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), _sample_result())
    try:
        db.commit()
    except IntegrityError:
        db.rollback()   # the unique constraint fired, as intended
    assert db.query(FareHistoryPoint).count() == 3


def test_ambiguous_multi_airport_history_is_not_misattributed():
    # When one search covered several destinations, the provider's
    # history can't be pinned to one of them -- so it must be skipped
    # rather than guessed at.
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import record_search_result, FareHistoryPoint
    db = _session()
    result = _sample_result()
    result.options[1].destination_airport = "INN"   # now two destinations
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), result)
    db.commit()
    assert db.query(FareHistoryPoint).count() == 0


def test_cheapest_observed_returns_lowest_recorded_fare():
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import record_search_result, cheapest_observed
    db = _session()
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), _sample_result())
    db.commit()
    assert cheapest_observed(db, "TLV", "GVA", date(2027, 1, 15), date(2027, 1, 20)) == 167


def test_cheapest_observed_is_none_for_an_unseen_route():
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import cheapest_observed
    db = _session()
    assert cheapest_observed(db, "TLV", "ZZZ", date(2027, 1, 15)) is None


def test_malformed_history_points_are_skipped_not_fatal():
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import record_search_result, FareHistoryPoint
    db = _session()
    result = _sample_result()
    result.insight.price_history = [
        [1766448000, 245],
        ["not-a-timestamp", 200],
        [1766534400, "not-a-price"],
        [1766620800, 167],
    ]
    record_search_result(db, "TLV", date(2027, 1, 15), date(2027, 1, 20), result)
    db.commit()
    assert db.query(FareHistoryPoint).count() == 2


def test_empty_result_records_nothing_without_crashing():
    _require_sqlalchemy()
    from ski_optimizer.db.fare_history import record_search_result
    db = _session()
    assert record_search_result(db, "TLV", date(2027, 1, 15), None,
                                 FlightSearchResult(options=[])) == 0
