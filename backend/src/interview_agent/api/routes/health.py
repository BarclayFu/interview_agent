import os
from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """存活探针：进程活着就返回 200。"""
    return {"status": "ok"}


@router.get("/version")
async def version() -> dict[str, str]:
    return {
        "version": os.getenv("GIT_SHA", "dev"),
        "built_at": os.getenv("BUILT_AT", datetime.now(UTC).isoformat()),
    }
