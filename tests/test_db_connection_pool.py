"""
The pool must survive an idle Neon compute.

FOUND IN PRODUCTION 2026-09-01: registering an account returned 500,
and the Cloud Run log showed

    psycopg2.OperationalError: SSL connection has been closed unexpectedly
    ski_optimizer/api/routes/auth.py:108 in register

Neon suspends idle compute and drops the TCP connection, but
SQLAlchemy's pool keeps handing the dead one out, so the FIRST request
after a quiet period fails -- login, register and search alike. Exactly
the traffic pattern this app has: a handful of users, long gaps.

pool_pre_ping issues a cheap liveness check and transparently replaces
a dead connection; pool_recycle retires them before the provider does.
"""
from ski_optimizer.db import database


def test_postgres_engines_pre_ping():
    kwargs = database.engine_kwargs("postgresql://user:pw@host/db")
    assert kwargs["pool_pre_ping"] is True, (
        "without pre-ping, the first request after an idle period gets a "
        "dead connection and 500s")
    assert 0 < kwargs["pool_recycle"] <= 600, (
        "connections must be retired before the provider drops them")
    assert kwargs["connect_args"] == {}, "check_same_thread is SQLite-only"


def test_sqlite_keeps_its_thread_flag_and_needs_no_recycling():
    kwargs = database.engine_kwargs("sqlite:///./ski_lab.db")
    assert kwargs["connect_args"] == {"check_same_thread": False}
    # Harmless on SQLite, and keeps one code path rather than two.
    assert kwargs["pool_pre_ping"] is True


def test_the_live_engine_is_built_with_those_settings():
    """The module-level engine is what the app actually uses."""
    assert database.engine.pool._pre_ping is True
