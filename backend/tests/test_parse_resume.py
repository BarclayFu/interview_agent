import uuid

import pytest

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import SINGLE_USER_ID, Resume
from interview_agent.worker.tasks import parse_resume

pytestmark = [pytest.mark.integration]


async def _new_resume(raw_text: str | None) -> uuid.UUID:
    async with get_session_factory()() as s:
        r = Resume(user_id=SINGLE_USER_ID, raw_text=raw_text, parse_status="pending")
        s.add(r)
        await s.commit()
        return r.id


async def test_parse_text_resume_done():
    rid = await _new_resume("王五 项目：支付系统 对账 清结算 " * 10)
    await parse_resume({}, str(rid))
    async with get_session_factory()() as s:
        r = await s.get(Resume, rid)
        assert r is not None and r.parse_status == "done" and r.parsed_projects


async def test_parse_resume_idempotent():
    rid = await _new_resume("赵六 项目：搜索 " * 10)
    await parse_resume({}, str(rid))
    async with get_session_factory()() as s:
        r = await s.get(Resume, rid)
        assert r is not None
        first = r.parsed_projects
    await parse_resume({}, str(rid))  # 重复消费
    async with get_session_factory()() as s:
        r = await s.get(Resume, rid)
        assert r is not None and r.parsed_projects == first
