"""观测 API 测试：/usage 聚合与 /debug 图状态（开发者面板数据源）。"""

import asyncio

import pytest
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app
from interview_agent.core.db import get_session_factory
from interview_agent.core.models import CostLedger
from interview_agent.engine.graph import reset_graph
from interview_agent.llm.ledger import Usage
from tests.helpers import ensure_session_rows, new_session_id

pytestmark = [pytest.mark.integration]


async def _add_ledger(sid: str, node: str, prompt: int, out: int, hit: int) -> None:
    u = Usage(
        session_id=sid,
        node=node,
        provider="deepseek",
        model="deepseek-chat",
        prompt_tokens=prompt,
        completion_tokens=out,
        latency_ms=123,
        cache_hit_tokens=hit,
        cache_miss_tokens=prompt - hit,
    )
    async with get_session_factory()() as s:
        s.add(
            CostLedger(
                session_id=sid,
                node=node,
                provider="deepseek",
                model="deepseek-chat",
                prompt_tokens=prompt,
                completion_tokens=out,
                cache_hit_tokens=hit,
                cache_miss_tokens=prompt - hit,
                cost_cny=u.cost_cny,
                latency_ms=123,
            )
        )
        await s.commit()


def test_session_usage_aggregates():
    sid = new_session_id()
    asyncio.run(ensure_session_rows(sid))
    asyncio.run(_add_ledger(sid, "ask", 1000, 100, 800))
    asyncio.run(_add_ledger(sid, "ask", 500, 50, 400))
    asyncio.run(_add_ledger(sid, "decide", 300, 30, 0))

    c = TestClient(create_app())
    body = c.get(f"/sessions/{sid}/usage").json()
    t = body["totals"]
    assert t["calls"] == 3
    assert t["prompt_tokens"] == 1800 and t["completion_tokens"] == 180
    assert t["cache_hit_tokens"] == 1200 and t["cache_miss_tokens"] == 600
    assert abs(t["cache_hit_rate"] - 0.667) < 0.01
    assert {b["node"] for b in body["by_node"]} == {"ask", "decide"}
    assert len(body["calls"]) == 3
    assert body["calls"][0]["latency_ms"] == 123


def test_session_debug_state_after_start():
    sid = new_session_id()
    asyncio.run(ensure_session_rows(sid))
    reset_graph()
    with TestClient(create_app()) as c:
        with c.stream("POST", f"/sessions/{sid}/turns", json={"action": "start"}) as r:
            for _ in r.iter_lines():
                pass
        body = c.get(f"/sessions/{sid}/debug").json()
        st = body["state"]
        assert st["phase"] == "deep_dive"
        assert st["question_count"] == 1
        assert st["project_count"] == 1
        assert body["paused_tasks"] == ["await_answer"]
        assert body["next"] == ["await_answer"]
    reset_graph()


def test_resume_raw_text_preview():
    c = TestClient(create_app())
    rid = c.post("/resumes", data={"text": "张三 项目：订单系统 " * 20}).json()["resume_id"]
    body = c.get(f"/resumes/{rid}").json()
    assert body["raw_text_preview"].startswith("张三")
    assert len(body["raw_text_preview"]) <= 500
