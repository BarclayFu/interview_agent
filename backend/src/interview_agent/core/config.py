from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# 必须用绝对路径：以 backend/ 为 CWD 启动时，相对 ".env" 读不到仓库根的 .env
_ENV_FILE = Path(__file__).resolve().parents[4] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, extra="ignore")

    app_env: str = "dev"
    # 本机 5432 常被其它项目占用，本项目 compose 映射到宿主机 5433
    database_url: str = "postgresql://postgres:postgres@localhost:5433/interview_agent"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"

    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str = "https://cloud.langfuse.com"
    otel_service_name: str = "interview-agent-api"

    # LLM（本地 .env 兼容两种命名：DEEPSEEK_API_KEY 或通用 API_KEY）
    deepseek_api_key: str | None = Field(
        default=None, validation_alias=AliasChoices("DEEPSEEK_API_KEY", "API_KEY")
    )
    deepseek_base_url: str = "https://api.deepseek.com"
    llm_model_chat: str = "deepseek-chat"
    llm_model_report: str = "deepseek-reasoner"
    use_stub_llm: bool = False

    # S3 兼容存储（dev: MinIO / prod: Supabase Storage）
    s3_endpoint_url: str = "http://localhost:9000"
    s3_bucket: str = "interview-agent"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_region: str = "us-east-1"

    # 安全：Vercel BFF 注入；为空则不强制（本地开发便利，生产必须配置）
    proxy_secret: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
