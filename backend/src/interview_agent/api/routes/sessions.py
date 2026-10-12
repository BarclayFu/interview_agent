"""会话端点（spec §6.1/§6.2）。SSE 翻译模式与 demo/app.py 一致：
stream_mode=["custom", "updates"]；custom 事件信封 → 同名 SSE；__interrupt__ → paused。

动作语义：
  start  —— 首次驱动图（initial state）；幂等保护：已有 checkpoint 则 409
  answer/hint/end —— Command(resume=...) 恢复图
  pause  —— 不驱动图，仅置 sessions.status=paused（checkpoint 本就持久化，「暂停」= 不再发回合）
"""

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from langgraph.types import Command
from pydantic import BaseModel
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from interview_agent.core.config import get_settings
from interview_agent.core.db import get_db, get_session_factory
from interview_agent.core.models import SINGLE_USER_ID, Report, Resume, Round, Session
from interview_agent.engine.graph import get_graph

router = APIRouter()


class CreateSessionReq(BaseModel):
    resume_id: uuid.UUID
    round_type: str = "project"


class TurnReq(BaseModel):
    action: str  # start / answer / hint / pause / end
    text: str = ""


def _sse(event: str, data: dict[str, Any]) -> dict[str, str]:
    return {"event": event, "data": json.dumps(data, ensure_ascii=False)}


def _graph_config(session_id: uuid.UUID) -> dict[str, Any]:
    cfg: dict[str, Any] = {"configurable": {"thread_id": str(session_id)}}
    s = get_settings()
    if s.langfuse_public_key and s.langfuse_secret_key:
        # 图内 LLM 调用入 Langfuse trace（spec §3.8/§5.5）
        from langfuse.langchain import CallbackHandler

        cfg["callbacks"] = [CallbackHandler()]
    return cfg


async def _stream_graph(inp: Any, config: dict[str, Any]) -> AsyncIterator[dict[str, str]]:
    graph = get_graph()
    try:
        async for mode, payload in graph.astream(inp, config, stream_mode=["custom", "updates"]):
            if mode == "custom":
                yield _sse(payload.get("event", "message"), payload.get("data", {}))
            elif mode == "updates" and "__interrupt__" in payload:
                yield _sse("paused", {"reason": "await_answer"})
        yield _sse("done", {})
    except Exception as exc:  # 异常也推给前端便于排查（event=error）
        yield _sse("error", {"message": f"{type(exc).__name__}: {exc}"})


@router.post("/sessions", status_code=201)
async def create_session(
    req: CreateSessionReq, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str]:
    resume = await db.get(Resume, req.resume_id)
    if resume is None:
        raise HTTPException(404, "resume not found")
    if resume.parse_status != "done" or not resume.parsed_projects:
        raise HTTPException(409, "简历尚未解析完成，稍后再试")
    sess = Session(user_id=SINGLE_USER_ID, resume_id=resume.id, round_type=req.round_type)
    db.add(sess)
    await db.flush()  # 先落 sessions 行，避免 rounds 外键失败
    db.add(Round(session_id=sess.id, type=req.round_type))
    await db.commit()
    return {"session_id": str(sess.id)}


@router.post("/sessions/{session_id}/turns")
async def turn(session_id: uuid.UUID, req: TurnReq) -> EventSourceResponse:
    config = _graph_config(session_id)
    now = datetime.now(UTC)

    if req.action == "pause":
        async with get_session_factory()() as s:
            await s.execute(
                update(Session)
                .where(Session.id == session_id)
                .values(status="paused", updated_at=now)
            )
            await s.commit()

        async def _paused() -> AsyncIterator[dict[str, str]]:
            yield _sse("paused", {"reason": "user"})
            yield _sse("done", {})

        return EventSourceResponse(_paused())

    async with get_session_factory()() as s:
        sess = await s.get(Session, session_id)
        if sess is None:
            raise HTTPException(404, "session not found")
        await s.execute(
            update(Session).where(Session.id == session_id).values(status="active", updated_at=now)
        )
        await s.commit()
        resume = await s.get(Resume, sess.resume_id)
        if resume is None:
            raise HTTPException(404, "resume not found")

    inp: Any
    if req.action == "start":
        graph = get_graph()
        snap = await graph.aget_state(config)
        if snap.values:  # 幂等：已有 checkpoint 的会话不允许重开
            raise HTTPException(409, "session already started")
        inp = {
            "session_id": str(session_id),
            "resume_summary": (resume.raw_text or "")[:1500],
            "projects": resume.parsed_projects,
            "max_questions": 8,
            "asked_questions": [],
            "scores": [],
            "transcript": [],
            "hint_count": 0,
            "question_count": 0,
            "followup_depth": 0,
            "current_project_idx": 0,
        }
    elif req.action in ("answer", "hint", "end"):
        inp = Command(resume={"action": req.action, "text": req.text})
    else:
        raise HTTPException(400, f"unknown action: {req.action}")

    return EventSourceResponse(_stream_graph(inp, config))


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: uuid.UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    sess = await db.get(Session, session_id)
    if sess is None:
        raise HTTPException(404, "session not found")
    graph = get_graph()
    snap = await graph.aget_state(_graph_config(session_id))
    values: dict[str, Any] = snap.values or {}
    messages = [
        {
            "role": "interviewer" if m.type == "ai" else "candidate",
            "content": str(m.content),
        }
        for m in values.get("transcript", [])
    ]
    report_status = (
        await db.execute(select(Report.status).where(Report.session_id == session_id))
    ).scalar_one_or_none()
    return {
        "session_id": str(sess.id),
        "status": sess.status,
        "phase": values.get("phase", "opening"),
        "question_count": values.get("question_count", 0),
        "messages": messages,
        "report_status": report_status,
    }


@router.get("/sessions")
async def list_sessions(db: Annotated[AsyncSession, Depends(get_db)]) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Session, Report.status)
            .outerjoin(Report, Report.session_id == Session.id)
            .order_by(desc(Session.created_at))
            .limit(20)
        )
    ).all()
    return [
        {
            "id": str(s.id),
            "status": s.status,
            "created_at": s.created_at.isoformat(),
            "report_status": rstatus,
        }
        for s, rstatus in rows
    ]
