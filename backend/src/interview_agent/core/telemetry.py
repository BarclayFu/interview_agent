from langfuse import Langfuse

from interview_agent.core.config import Settings


def init_telemetry(settings: Settings) -> Langfuse | None:
    """初始化 Langfuse（v4，OTel 原生）。未配置密钥时返回 None，本地开发不导出。"""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        base_url=settings.langfuse_base_url,
    )
