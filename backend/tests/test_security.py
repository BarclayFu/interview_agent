import pytest
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app
from interview_agent.core.config import get_settings

PROTECTED = ["/resumes", "/sessions"]


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    """monkeypatch 的 env 在用例后还原，但 lru_cache 不会；手动清，防污染后续用例。"""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _client(monkeypatch, secret: str | None) -> TestClient:
    get_settings.cache_clear()
    if secret is None:
        monkeypatch.delenv("PROXY_SECRET", raising=False)
    else:
        monkeypatch.setenv("PROXY_SECRET", secret)
    return TestClient(create_app())


def test_open_endpoints_never_blocked(monkeypatch):
    c = _client(monkeypatch, "s3cret")
    assert c.get("/healthz").status_code == 200
    assert c.get("/version").status_code == 200


def test_protected_blocked_without_header(monkeypatch):
    c = _client(monkeypatch, "s3cret")
    for path in PROTECTED:
        assert c.get(path).status_code == 401


def test_protected_allowed_with_header(monkeypatch):
    c = _client(monkeypatch, "s3cret")
    r = c.get("/sessions", headers={"X-Proxy-Secret": "s3cret"})
    assert r.status_code != 401  # 路由逻辑另测；此处只验不被中间件拦


def test_permissive_when_unset(monkeypatch):
    c = _client(monkeypatch, None)
    assert c.get("/sessions").status_code != 401
