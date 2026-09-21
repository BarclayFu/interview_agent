import os

from interview_agent.core.config import Settings


def init_telemetry(settings: Settings) -> None:
    """把 Langfuse 配置桥接进环境变量。

    @observe() 使用 Langfuse 的模块级单例，而单例只读 os.environ；pydantic-settings
    从 .env 读到的值不会自动进入环境变量，故在此显式补齐（已存在的环境变量优先）。
    单例是惰性创建的，应用启动时调用本函数即可在其创建前生效。
    """
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", settings.langfuse_base_url)
