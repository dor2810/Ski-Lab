"""
Database engine and session setup.

Defaults to a local SQLite file (zero setup for dev) and reads
DATABASE_URL from the environment when present, so switching to
Postgres later (Phase 8's full schema) is a config change, not a code
change -- point DATABASE_URL at Postgres and nothing else here needs
to move.

This is the auth-only slice of Phase 8, not the full blueprint schema
(SkiResort, Trip, TripOption, Price, etc. from Section 6). Those stay
in the spreadsheet until there's a real reason to migrate them (see
db/__init__.py). Mixing "just enough DB for real accounts" with "the
whole resort database" in one migration would be a much bigger, riskier
change than the current step calls for.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ski_lab.db")

# How long a pooled connection may live. Neon parks idle compute and
# drops the socket well before an hour, so connections are retired on
# our side first.
_POOL_RECYCLE_SECONDS = 300


def engine_kwargs(url: str) -> dict:
    """
    How to build the engine for a given database URL.

    pool_pre_ping IS NOT OPTIONAL HERE. Without it, SQLAlchemy hands out
    whatever is in the pool, including a connection the provider has
    already closed. Measured in production 2026-09-01: POST /auth/register
    returned 500 with

        psycopg2.OperationalError: SSL connection has been closed unexpectedly

    because Neon had suspended the compute between requests. This app's
    traffic is a few users with long gaps -- precisely the pattern that
    keeps a pooled connection sitting idle until it is dead. Pre-ping
    costs one trivial round trip and transparently replaces it.

    Separated from the module-level engine below so the settings can be
    asserted without a live database (see
    tests/test_db_connection_pool.py).
    """
    is_sqlite = url.startswith("sqlite")
    return {
        # SQLite needs this flag when used from multiple threads (FastAPI's
        # default threadpool for sync routes); Postgres doesn't accept it.
        "connect_args": {"check_same_thread": False} if is_sqlite else {},
        "pool_pre_ping": True,
        "pool_recycle": _POOL_RECYCLE_SECONDS,
    }


engine = create_engine(DATABASE_URL, **engine_kwargs(DATABASE_URL))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """
    Creates tables if they don't exist. Fine for SQLite dev; once this
    is backed by Postgres for real, use alembic migrations instead of
    this (see db/__init__.py's migrations/ note) -- create_all() has no
    concept of altering an existing table, only creating missing ones.
    """
    from . import models  # noqa: F401 -- import registers models on Base.metadata
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a session, always closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope():
    """For use outside FastAPI's dependency system (scripts, tests)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
