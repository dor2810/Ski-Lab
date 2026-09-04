"""
/health has to fail when the app is actually broken.

It returned {"status": "ok"} unconditionally -- a constant, checking
nothing. On 2026-09-01 registration was returning 500 because the
pooled Postgres connection was dead, and this endpoint would have gone
on reporting "ok" throughout. An alarm wired to it would have been
theatre.

The database is the dependency that broke and the one every real
request needs, so that is what it checks.
"""
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

from fastapi.testclient import TestClient

from ski_optimizer.api import main


def test_healthy_when_the_database_answers():
    with TestClient(main.app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"


def test_degraded_and_503_when_the_database_is_unreachable(monkeypatch):
    """503 rather than 200-with-a-sad-body: an uptime check watches the
    STATUS CODE, and a monitor that has to parse JSON to notice an
    outage is one nobody wires up correctly."""
    def dead(*a, **k):
        raise RuntimeError("SSL connection has been closed unexpectedly")
    monkeypatch.setattr(main, "_database_ok", dead)

    with TestClient(main.app) as client:
        r = client.get("/health")
    assert r.status_code == 503, "a broken dependency must show in the status code"
    assert r.json()["status"] == "degraded"
    assert "database" in r.json()["checks"]
