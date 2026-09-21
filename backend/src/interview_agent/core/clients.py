import asyncpg
from redis.asyncio import Redis

from interview_agent.core.config import Settings


def normalize_pg_dsn(url: str) -> str:
    """asyncpg 只认 postgresql:// / postgres://，不认 SQLAlchemy 的 +asyncpg 后缀。"""
    return url.replace("postgresql+asyncpg://", "postgresql://")


async def check_postgres(settings: Settings) -> None:
    conn = await asyncpg.connect(dsn=normalize_pg_dsn(settings.database_url), timeout=3)
    try:
        await conn.fetchval("SELECT 1")
    finally:
        await conn.close()


async def check_redis(settings: Settings) -> None:
    client = Redis.from_url(settings.redis_url, socket_timeout=3)
    try:
        await client.ping()
    finally:
        await client.aclose()
