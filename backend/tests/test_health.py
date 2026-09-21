from fastapi.testclient import TestClient

from interview_agent.api.app import create_app

client = TestClient(create_app())


def test_healthz_returns_ok():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_version_returns_sha_and_built_at():
    r = client.get("/version")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"version", "built_at"}
