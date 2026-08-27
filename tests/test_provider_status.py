"""
Tests for engine/provider_status.py -- reporting that live pricing was
blocked, rather than silently degrading to estimates.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from concurrent.futures import ThreadPoolExecutor

from ski_optimizer.engine.provider_status import (
    reset_provider_status, note_provider_blocked, was_provider_blocked,
)


def test_starts_clean_after_reset():
    note_provider_blocked()
    reset_provider_status()
    assert was_provider_blocked() is False


def test_records_a_block():
    reset_provider_status()
    note_provider_blocked()
    assert was_provider_blocked() is True


def test_a_block_flagged_inside_a_worker_thread_is_visible_to_the_caller():
    """
    REGRESSION, and the whole reason this module isn't a ContextVar.

    Live repricing runs on a ThreadPoolExecutor. The first version used
    a ContextVar on the assumption that the pool propagates context into
    its workers -- it does NOT, and a value set inside a worker cannot
    travel back to the submitting thread regardless. So every block was
    recorded where nobody would read it: the server logged "live flight
    pricing BLOCKED" while the API response reported
    live_pricing_blocked=false. Found by diffing the production logs
    against the production response.
    """
    reset_provider_status()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: note_provider_blocked(), range(3)))
    assert was_provider_blocked() is True, (
        "a block flagged in a worker thread must be visible to the request thread"
    )


def test_reset_clears_state_left_by_a_previous_request():
    reset_provider_status()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda _: note_provider_blocked(), range(2)))
    assert was_provider_blocked() is True
    reset_provider_status()
    assert was_provider_blocked() is False, "state must not leak into the next request"
