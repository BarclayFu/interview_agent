import os

from interview_agent.core.config import Settings
from interview_agent.core.telemetry import init_telemetry


def test_noop_when_keys_missing(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    settings = Settings(langfuse_public_key=None, langfuse_secret_key=None)
    init_telemetry(settings)
    assert "LANGFUSE_PUBLIC_KEY" not in os.environ


def test_bridges_settings_into_env(monkeypatch):
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    settings = Settings(langfuse_public_key="pk-lf-test", langfuse_secret_key="sk-lf-test")
    init_telemetry(settings)
    assert os.environ["LANGFUSE_PUBLIC_KEY"] == "pk-lf-test"
    assert os.environ["LANGFUSE_SECRET_KEY"] == "sk-lf-test"
