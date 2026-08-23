"""
Short-TTL response cache for adapter calls.

WHY THIS IS ITS OWN MODULE, separate from fare persistence: these are
two genuinely different jobs that were conflated in the adapter's first
version, and mixing them is a design error.

  - THIS file: "don't pay for the same search twice." Ephemeral,
    short-lived, and completely fine to lose -- a cold cache costs
    money and latency, never correctness.
  - db/fare_history.py: "own our price data forever." Permanent,
    append-only, and the thing that stops our differentiator being
    rented from a provider.

Different lifetimes, different failure modes, different storage. Kept apart.

The original in-memory dict had a real bug: TTL was only checked on
READ, so an entry never read again stayed forever. Verified: 500 stale
inserts left 500 entries, all expired, none evicted. A slow leak in a
long-running server. This implementation is bounded with LRU eviction
and prunes expired entries as it goes.

BACKEND SWAP: MemoryResponseCache is the default (zero infrastructure).
The architecture plan calls for Redis in production; implement
RedisResponseCache against the same three methods (get/set/clear) and
swap it in via set_cache() -- nothing in adapters/ changes.
"""
import threading
import time
from collections import OrderedDict
from typing import Any, Optional


class ResponseCache:
    """Interface every cache backend implements. See module docstring."""

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any) -> None:
        raise NotImplementedError

    def clear(self) -> None:
        raise NotImplementedError


class MemoryResponseCache(ResponseCache):
    """
    Bounded, thread-safe, TTL'd LRU cache.

    Thread-safe because FastAPI serves sync routes from a threadpool --
    concurrent searches genuinely can hit this at the same time, and an
    OrderedDict mutated from two threads can corrupt.
    """

    def __init__(self, max_entries: int = 512, ttl_seconds: int = 3600):
        if max_entries <= 0:
            raise ValueError(f"max_entries must be > 0, got {max_entries}")
        if ttl_seconds <= 0:
            raise ValueError(f"ttl_seconds must be > 0, got {ttl_seconds}")
        self.max_entries = max_entries
        self.ttl_seconds = ttl_seconds
        self._data: "OrderedDict[str, tuple]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    def _is_expired(self, stored_at: float) -> bool:
        return (time.time() - stored_at) >= self.ttl_seconds

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                self.misses += 1
                return None
            stored_at, value = entry
            if self._is_expired(stored_at):
                # Evict on read too -- don't leave known-dead entries
                # occupying the bound.
                del self._data[key]
                self.misses += 1
                return None
            self._data.move_to_end(key)  # mark as recently used
            self.hits += 1
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            if key in self._data:
                del self._data[key]
            self._data[key] = (time.time(), value)
            self._prune_locked()

    def _prune_locked(self) -> None:
        """Drop expired entries first, then LRU-evict down to the bound."""
        now = time.time()
        expired = [k for k, (t, _) in self._data.items()
                   if (now - t) >= self.ttl_seconds]
        for k in expired:
            del self._data[k]
        while len(self._data) > self.max_entries:
            self._data.popitem(last=False)  # oldest / least recently used

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
            self.hits = 0
            self.misses = 0

    def stats(self) -> dict:
        """For observability -- a low hit rate means we're burning API quota."""
        with self._lock:
            total = self.hits + self.misses
            return {
                "entries": len(self._data),
                "max_entries": self.max_entries,
                "ttl_seconds": self.ttl_seconds,
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": (self.hits / total) if total else 0.0,
            }

    def __len__(self) -> int:
        with self._lock:
            return len(self._data)


_active_cache: ResponseCache = MemoryResponseCache()


def get_cache() -> ResponseCache:
    return _active_cache


def set_cache(cache: ResponseCache) -> None:
    """Swap the backend (Redis in production, a fake in tests)."""
    global _active_cache
    _active_cache = cache
