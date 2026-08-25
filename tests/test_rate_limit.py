"""
Tests for api/rate_limit.py's RateLimiter -- pure logic, no FastAPI
involved, run fully offline.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ski_optimizer.api.rate_limit import RateLimiter, live_pricing_allowed, clear_all, _DAILY_LIVE_LIMIT


def test_allows_up_to_the_limit():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    assert rl.allow("a") is True
    assert rl.allow("a") is True
    assert rl.allow("a") is True


def test_rejects_once_the_limit_is_hit():
    rl = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        rl.allow("a")
    assert rl.allow("a") is False


def test_rejected_attempts_dont_consume_budget():
    # A rejected call must not itself count toward the window -- only
    # successful (allowed) hits do. Otherwise a client hammering past
    # the limit would never recover even after the window elapses.
    rl = RateLimiter(max_requests=2, window_seconds=60)
    assert rl.allow("a") is True
    assert rl.allow("a") is True
    for _ in range(10):
        assert rl.allow("a") is False
    # Still exactly 2 real hits recorded, not 12.
    assert len(rl._hits["a"]) == 2


def test_keys_are_independent():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    assert rl.allow("a") is True
    assert rl.allow("b") is True  # different key, unaffected by "a"'s usage
    assert rl.allow("a") is False
    assert rl.allow("b") is False


def test_old_hits_age_out_of_the_window():
    rl = RateLimiter(max_requests=1, window_seconds=0.05)
    assert rl.allow("a") is True
    assert rl.allow("a") is False
    time.sleep(0.06)
    assert rl.allow("a") is True  # the old hit has aged out


def test_clear_resets_all_keys():
    rl = RateLimiter(max_requests=1, window_seconds=60)
    rl.allow("a")
    rl.allow("b")
    assert rl.allow("a") is False
    rl.clear()
    assert rl.allow("a") is True
    assert rl.allow("b") is True


def test_live_pricing_allowed_exhausts_the_global_daily_budget():
    # The global gate specifically -- NOT per-key, one shared budget
    # across all callers, matching the real constraint (SerpApi's quota
    # is global, not per-visitor).
    clear_all()
    try:
        for _ in range(_DAILY_LIVE_LIMIT):
            assert live_pricing_allowed() is True
        assert live_pricing_allowed() is False
    finally:
        clear_all()


def test_rejects_nonpositive_construction_args():
    for kwargs in (dict(max_requests=0, window_seconds=60), dict(max_requests=5, window_seconds=0)):
        try:
            RateLimiter(**kwargs)
            assert False, f"expected ValueError for {kwargs}"
        except ValueError:
            pass
