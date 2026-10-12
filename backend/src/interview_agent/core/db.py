"""SQLAlchemy async 装配。settings.database_url 是标准 postgresql:// 串，
SQLAlchemy async 需要 +asyncpg 驱动后缀；checkpointer（psycopg）则直接用原串。"""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from interview_agent.core.config import get_settings


def async_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


# NullPool：不缓存连接。理由：asyncpg 连接绑定创建它的事件循环，跨 loop（pytest 多 loop、
# TestClient 独立 loop）会 RuntimeError；生产侧已有 Supavisor pooler 做池化，应用侧自建池无必要。
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine, _session_factory
    if _engine is None:
        _engine = create_async_engine(async_url(get_settings().database_url), poolclass=NullPool)
        _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _session_factory is not None
    return _session_factory


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：每请求一个 session。"""
    async with get_session_factory()() as session:
        yield session
