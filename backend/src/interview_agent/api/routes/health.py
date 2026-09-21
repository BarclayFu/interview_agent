import asyncio
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from langfuse import observe

from interview_agent.core.clients import check_postgres, check_redis
from interview_agent.core.config import Settings, get_settings

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """存活探针：进程活着就返回 200。"""
    return {"status": "ok"}


@router.get("/readyz")
async def readyz(response: Response) -> dict[str, str]:
    """就绪探针：任一依赖不可用即 503（接 K8s readinessProbe）。"""
    settings = get_settings()

    async def probe(fn: Callable[[Settings], Awaitable[None]]) -> str:
        try:
            await fn(settings)
            return "ok"
        except Exception:
            return "error"

    db, redis = await asyncio.gather(probe(check_postgres), probe(check_redis))
    result = {"db": db, "redis": redis}
    if "error" in result.values():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@router.get("/version")
@observe()
async def version() -> dict[str, str]:
    return {
        "version": os.getenv("GIT_SHA", "dev"),
        "built_at": os.getenv("BUILT_AT", datetime.now(UTC).isoformat()),
    }
