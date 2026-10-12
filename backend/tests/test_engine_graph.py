import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from interview_agent.engine.graph import build_project_graph
from tests.helpers import ensure_session_rows, initial_state, new_session_id

pytestmark = [pytest.mark.integration]  # ledger 落库需 PG


async def _run_until_interrupt(graph, inp, config) -> dict:
    async for _, payload in graph.astream(inp, config, stream_mode=["updates"]):
        if "__interrupt__" in payload:
            return payload["__interrupt__"][0].value
    raise AssertionError("图未在 await_answer 处 interrupt")


async def test_full_flow_answer_then_close_by_cap():
    sid = new_session_id()
    await ensure_session_rows(sid)
    graph = build_project_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": sid}}

    intr = await _run_until_interrupt(graph, initial_state(sid), cfg)
    assert intr["event"] == "await_answer" and intr["question"]

    # 回答一次 → decide → 未到上限继续出题 → 再 interrupt
    intr = await _run_until_interrupt(
        graph, Command(resume={"action": "answer", "text": "架构是……" * 30}), cfg
    )
    assert intr["question"]

    # 再答一次 → 达 max_questions=2 → closing → END（无更多 interrupt）
    async for _, payload in graph.astream(
        Command(resume={"action": "answer", "text": "细节……" * 30}), cfg, stream_mode=["updates"]
    ):
        if "__interrupt__" in payload:
            raise AssertionError("达上限后不应再等回答")
    snap = await graph.aget_state(cfg)
    assert snap.values["question_count"] == 2
    assert snap.values["phase"] == "closing"
    assert len(snap.values["scores"]) == 2


async def test_hint_loop_returns_to_await():
    sid = new_session_id()
    await ensure_session_rows(sid)
    graph = build_project_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": sid}}
    await _run_until_interrupt(graph, initial_state(sid), cfg)

    intr = await _run_until_interrupt(graph, Command(resume={"action": "hint", "text": ""}), cfg)
    assert intr["event"] == "await_answer"
    snap = await graph.aget_state(cfg)
    assert snap.values["hint_count"] == 1


async def test_end_action_goes_closing():
    sid = new_session_id()
    await ensure_session_rows(sid)
    graph = build_project_graph(MemorySaver())
    cfg = {"configurable": {"thread_id": sid}}
    await _run_until_interrupt(graph, initial_state(sid), cfg)

    async for _ in graph.astream(
        Command(resume={"action": "end", "text": ""}), cfg, stream_mode=["updates"]
    ):
        pass
    snap = await graph.aget_state(cfg)
    assert snap.values["phase"] == "closing" and not snap.next
