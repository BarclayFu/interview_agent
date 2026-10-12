import json

import pytest
from fastapi.testclient import TestClient

from interview_agent.api.app import create_app
from interview_agent.core.db import get_session_factory
from interview_agent.core.models import SINGLE_USER_ID, Resume
from interview_agent.engine.graph import reset_graph

pytestmark = [pytest.mark.integration]


@pytest.fixture
def client():
    reset_graph()
    with TestClient(create_app()) as c:  # with：跑 lifespan（checkpointer 初始化/关闭）
        yield c
    reset_graph()


async def _done_resume() -> str:
    async with get_session_factory()() as s:
        r = Resume(
            user_id=SINGLE_USER_ID,
            raw_text="x",
            parse_status="done",
            parsed_projects=[
                {"name": "订单系统", "role": "负责人", "tech": ["Python"], "claims": ["QPS x3"]}
            ],
        )
        s.add(r)
        await s.commit()
        return str(r.id)


def _sse_events(resp) -> list[dict]:
    events = []
    event = None
    for raw in resp.iter_lines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event:
            events.append({"event": event, "data": json.loads(line.split(":", 1)[1])})
            event = None
    return events


async def test_session_lifecycle_over_sse(client):
    rid = await _done_resume()
    sid = client.post("/sessions", json={"resume_id": rid}).json()["session_id"]

    with client.stream("POST", f"/sessions/{sid}/turns", json={"action": "start"}) as r:
        assert r.status_code == 200
        events = _sse_events(r)
    names = [e["event"] for e in events]
    assert "token" in names and "question" in names and "done" in names

    with client.stream(
        "POST", f"/sessions/{sid}/turns", json={"action": "answer", "text": "架构是……" * 30}
    ) as r:
        events2 = _sse_events(r)
    assert any(e["event"] == "feedback" for e in events2)

    with client.stream("POST", f"/sessions/{sid}/turns", json={"action": "end"}) as r:
        events3 = _sse_events(r)
    assert any(e["event"] == "finished" for e in events3)

    st = client.get(f"/sessions/{sid}").json()
    assert st["status"] == "finished" and st["messages"]


async def test_create_session_rejects_unparsed_resume(client):
    async with get_session_factory()() as s:
        r = Resume(user_id=SINGLE_USER_ID, raw_text="x", parse_status="pending")
        s.add(r)
        await s.commit()
        rid = str(r.id)
    assert client.post("/sessions", json={"resume_id": rid}).status_code == 409


def test_list_sessions(client):
    r = client.get("/sessions")
    assert r.status_code == 200 and isinstance(r.json(), list)
