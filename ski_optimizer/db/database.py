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

# SQLite needs this flag when used from multiple threads (FastAPI's default
# threadpool for sync routes); Postgres doesn't need or accept it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
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
