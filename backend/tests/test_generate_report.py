import uuid

import pytest
from sqlalchemy import select

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import (
    SINGLE_USER_ID,
    Message,
    Report,
    Resume,
    Round,
    Session,
)
from interview_agent.worker.tasks import generate_report

pytestmark = [pytest.mark.integration]


async def _finished_session_with_messages() -> str:
    async with get_session_factory()() as s:
        r = Resume(
            user_id=SINGLE_USER_ID,
            raw_text="x",
            parse_status="done",
            parsed_projects=[{"name": "订单系统"}],
        )
        s.add(r)
        await s.flush()
        sess = Session(user_id=SINGLE_USER_ID, resume_id=r.id, status="finished")
        s.add(sess)
        await s.flush()
        rnd = Round(
            session_id=sess.id,
            type="project",
            status="finished",
            scores={"items": [{"question": "架构？", "score": 6}]},
        )
        s.add(rnd)
        await s.flush()
        for i, (role, kind, content) in enumerate(
            [
                ("interviewer", "question", "介绍一下订单系统架构？"),
                (
                    "candidate",
                    "answer",
                    "我们拆成了订单、库存、支付三个服务，用 MQ 解耦，QPS 提升3倍。",
                ),
                ("interviewer", "question", "QPS 提升3倍怎么测出来的？"),
                ("candidate", "answer", "压测对比，旧链路 800，新链路 2400。"),
            ]
        ):
            s.add(
                Message(
                    session_id=sess.id,
                    round_id=rnd.id,
                    seq=i,
                    role=role,
                    kind=kind,
                    content=content,
                )
            )
        s.add(Report(session_id=sess.id, status="pending"))
        await s.commit()
        return str(sess.id)


async def test_generate_report_done():
    sid = await _finished_session_with_messages()
    await generate_report({}, sid, 1)
    async with get_session_factory()() as s:
        rep = (
            await s.execute(select(Report).where(Report.session_id == uuid.UUID(sid)))
        ).scalar_one()
        assert rep.status == "done"
        assert rep.report and rep.report["schema_version"] == 1
        assert "dimensions" in rep.report and "highlights" in rep.report


async def test_generate_report_idempotent():
    sid = await _finished_session_with_messages()
    await generate_report({}, sid, 1)
    async with get_session_factory()() as s:
        rep = (
            await s.execute(select(Report).where(Report.session_id == uuid.UUID(sid)))
        ).scalar_one()
        first = rep.report
    await generate_report({}, sid, 1)  # 重复消费
    async with get_session_factory()() as s:
        rows = (
            (await s.execute(select(Report).where(Report.session_id == uuid.UUID(sid))))
            .scalars()
            .all()
        )
        assert len(rows) == 1 and rows[0].report == first
