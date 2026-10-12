"""报告查询（spec §6.1）：生成中 202、完成 200、不存在 404。"""

import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from interview_agent.core.db import get_db
from interview_agent.core.models import Report

router = APIRouter()


@router.get("/sessions/{session_id}/report", response_model=None)
async def get_report(
    session_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> Response | dict[str, Any]:
    rep = (
        await db.execute(select(Report).where(Report.session_id == session_id))
    ).scalar_one_or_none()
    if rep is None:
        raise HTTPException(404, "report not found")
    if rep.status != "done":
        return Response(
            content=json.dumps({"status": rep.status}),
            status_code=202,
            media_type="application/json",
        )
    return {"status": "done", "report": rep.report, "model": rep.model}
