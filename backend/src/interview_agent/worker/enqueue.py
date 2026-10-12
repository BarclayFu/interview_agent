"""arq 连接池与入队助手。API 与 engine 共用。

不缓存连接池：redis-py 连接绑定事件循环，跨 loop（pytest 多 loop / TestClient）会炸；
单用户场景下每次建连开销可忽略。_job_id 去重是「幂等第一道闸」。
"""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from interview_agent.core.config import get_settings


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


async def _enqueue(name: str, *args: object, job_id: str | None = None) -> None:
    pool: ArqRedis = await create_pool(_redis_settings())
    try:
        await pool.enqueue_job(name, *args, _job_id=job_id)
    finally:
        await pool.aclose()


async def enqueue_parse_resume(resume_id: str) -> None:
    await _enqueue("parse_resume", resume_id)


async def enqueue_generate_report(session_id: str, attempt: int = 1) -> None:
    await _enqueue("generate_report", session_id, attempt, job_id=f"report:{session_id}")
