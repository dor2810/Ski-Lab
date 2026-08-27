"""
Per-request record of whether a live-pricing provider blocked us.

WHY THIS EXISTS: live flight pricing is a scraper, and Google answers
suspected automation with a CAPTCHA page. Every blocked lookup degrades
into a static estimate labelled "EST." -- which is technically true and
completely unhelpful, because it looks identical to "we checked and
this is our best guess." The user cannot tell "no live price exists"
from "we were locked out." This project's rule is to degrade VISIBLY,
so the fact is recorded and reported alongside the results.

WHY A LIST AND NOT A ContextVar -- this is the interesting part, and it
was a real bug before it was a design note.

The first version used a ContextVar, on the assumption that
ThreadPoolExecutor propagates context into its workers. IT DOES NOT.
Context propagation into threads has to be arranged explicitly, and
even then a value set INSIDE a worker cannot travel back out to the
submitting thread -- each thread's context is its own. Live repricing
runs entirely on a thread pool, so every block was recorded in a
context nobody would ever read: the server logged "live flight pricing
BLOCKED" while the API response cheerfully reported
live_pricing_blocked=false. Caught by diffing the production logs
against the production response, rather than trusting the deploy.

A module-level list works because the only write is append, which is
atomic under the GIL, and readers only ask "is it non-empty". Callers
must reset() at the start of a request. That does mean two genuinely
simultaneous requests share the flag: the cost is that one request may
report a block another request hit, which OVER-reports honesty rather
than under-reporting it -- a far better failure than the silent EST.
wall this replaced.
"""
from typing import List

# Append-only within a request; reset between requests. See docstring
# for why this is a plain list rather than a ContextVar.
_BLOCK_SIGNAL: List[bool] = []


def reset_provider_status() -> None:
    """Call at the START of a request, before any live pricing runs."""
    _BLOCK_SIGNAL.clear()


def note_provider_blocked() -> None:
    """Record that a live-pricing provider served an anti-bot challenge."""
    _BLOCK_SIGNAL.append(True)


def was_provider_blocked() -> bool:
    """Whether any live-pricing lookup in this request hit a block."""
    return bool(_BLOCK_SIGNAL)
