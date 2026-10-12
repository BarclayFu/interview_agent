"""M1 纵切集成测试：StubProvider，真实 PG/Redis/MinIO（compose）。"""

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from interview_agent.api.app import create_app
from interview_agent.core.db import get_session_factory
from interview_agent.core.models import CostLedger
from interview_agent.engine.graph import reset_graph

pytestmark = [pytest.mark.integration]


def _events(resp) -> list[str]:
    names = []
    for line in resp.iter_lines():
        if line.startswith("event:"):
            names.append(line.split(":", 1)[1].strip())
    return names


def test_full_vertical_slice():
    reset_graph()
    with TestClient(create_app()) as client:  # with：跑 lifespan（checkpointer 初始化）
        # 1) 上传文本简历 → 解析任务同步执行（测试直调任务函数，不依赖 arq worker 进程）
        rid = client.post("/resumes", data={"text": "张三 订单系统 QPS 提升3倍 " * 10}).json()[
            "resume_id"
        ]
        from interview_agent.worker.tasks import generate_report, parse_resume

        asyncio.run(parse_resume({}, rid))
        assert client.get(f"/resumes/{rid}").json()["parse_status"] == "done"

        # 2) 开会话 → start（SSE）
        sid = client.post("/sessions", json={"resume_id": rid}).json()["session_id"]
        with client.stream("POST", f"/sessions/{sid}/turns", json={"action": "start"}) as r:
            assert "question" in _events(r)

        # 3) 两回合回答
        for _ in range(2):
            with client.stream(
                "POST",
                f"/sessions/{sid}/turns",
                json={"action": "answer", "text": "架构与取舍……QPS 提升3倍" * 10},
            ) as r:
                _events(r)

        # 4) 结束 → finalize 落库 + 入队 → 报告任务
        with client.stream("POST", f"/sessions/{sid}/turns", json={"action": "end"}) as r:
            assert "finished" in _events(r)
        asyncio.run(generate_report({}, sid, 1))
        rep = client.get(f"/sessions/{sid}/report").json()
        assert rep["status"] == "done" and rep["report"]["schema_version"] == 1

        # 5) 成本记账存在（Stub 也记账）
        async def _count() -> int:
            async with get_session_factory()() as s:
                return len((await s.execute(select(CostLedger))).scalars().all())

        assert asyncio.run(_count()) > 0
    reset_graph()
