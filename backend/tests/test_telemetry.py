from interview_agent.core.config import Settings
from interview_agent.core.telemetry import init_telemetry


def test_returns_none_when_keys_missing():
    settings = Settings(langfuse_public_key=None, langfuse_secret_key=None)
    assert init_telemetry(settings) is None


def test_returns_client_when_keys_present():
    settings = Settings(langfuse_public_key="pk-lf-test", langfuse_secret_key="sk-lf-test")
    client = init_telemetry(settings)
    assert client is not None
