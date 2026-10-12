"""引擎测试共用：合法 UUID 会话 + DB 行准备 + 初始状态。"""

import uuid
from typing import Any

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import SINGLE_USER_ID, Resume, Round, Session


def new_session_id() -> str:
    return str(uuid.uuid4())


async def ensure_session_rows(session_id: str) -> None:
    """finalize 会写 rounds/sessions/reports，测试里先把行建好。"""
    sid = uuid.UUID(session_id)
    async with get_session_factory()() as s:
        if await s.get(Session, sid) is not None:
            return
        r = Resume(
            user_id=SINGLE_USER_ID,
            raw_text="x",
            parse_status="done",
            parsed_projects=[{"name": "订单系统"}],
        )
        s.add(r)
        await s.flush()
        s.add(Session(id=sid, user_id=SINGLE_USER_ID, resume_id=r.id))
        await s.flush()
        s.add(Round(session_id=sid, type="project"))
        await s.commit()


def initial_state(session_id: str, max_questions: int = 2) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "resume_summary": "张三，后端，订单系统/网关两个项目",
        "projects": [
            {
                "name": "订单系统",
                "role": "后端负责人",
                "tech": ["Python", "PG"],
                "claims": ["QPS 提升3倍"],
            },
            {"name": "API 网关", "role": "核心开发", "tech": ["Go"], "claims": []},
        ],
        "max_questions": max_questions,
        "asked_questions": [],
        "scores": [],
        "transcript": [],
        "hint_count": 0,
        "question_count": 0,
        "followup_depth": 0,
        "current_project_idx": 0,
    }
