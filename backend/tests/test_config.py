from interview_agent.core.config import Settings


def test_cors_origins_parsed_into_list():
    s = Settings(cors_origins="http://localhost:3000, https://foo.vercel.app")
    assert s.cors_origin_list == ["http://localhost:3000", "https://foo.vercel.app"]


def test_defaults_are_local():
    s = Settings()
    assert s.app_env == "dev"
    assert s.database_url.startswith("postgresql://")
    assert s.redis_url.startswith("redis://")
