from fastapi.testclient import TestClient

from interview_agent.api.app import create_app
from interview_agent.api.routes import health

client = TestClient(create_app())


async def _ok(_settings) -> None:
    return None


async def _fail(_settings) -> None:
    raise RuntimeError("boom")


def test_readyz_ok(monkeypatch):
    monkeypatch.setattr(health, "check_postgres", _ok)
    monkeypatch.setattr(health, "check_redis", _ok)
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"db": "ok", "redis": "ok"}


def test_readyz_marks_db_error_and_returns_503(monkeypatch):
    monkeypatch.setattr(health, "check_postgres", _fail)
    monkeypatch.setattr(health, "check_redis", _ok)
    r = client.get("/readyz")
    assert r.status_code == 503
    assert r.json() == {"db": "error", "redis": "ok"}
