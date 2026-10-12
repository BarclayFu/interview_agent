import pytest
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg import AsyncConnection
from psycopg.rows import dict_row

from interview_agent.core.config import get_settings
from interview_agent.engine.graph import build_project_graph
from tests.helpers import ensure_session_rows, initial_state, new_session_id

pytestmark = [pytest.mark.integration]


async def _new_saver() -> AsyncPostgresSaver:
    conn = await AsyncConnection.connect(
        get_settings().database_url, autocommit=True, row_factory=dict_row
    )
    saver = AsyncPostgresSaver(conn)
    await saver.setup()
    return saver


async def test_resume_across_process_restart():
    """模拟进程重启：第一个 saver 跑到 interrupt；新建 saver/图实例（同库同 thread_id）恢复。"""
    sid = new_session_id()
    await ensure_session_rows(sid)
    cfg = {"configurable": {"thread_id": sid}}

    g1 = build_project_graph(await _new_saver())
    async for _, payload in g1.astream(initial_state(sid), cfg, stream_mode=["updates"]):
        if "__interrupt__" in payload:
            break

    g2 = build_project_graph(await _new_saver())  # 新连接新图 = 「另一个进程」
    async for _, payload in g2.astream(
        Command(resume={"action": "answer", "text": "架构是微服务拆分……" * 10}),
        cfg,
        stream_mode=["updates"],
    ):
        if "__interrupt__" in payload:
            break
    snap = await g2.aget_state(cfg)
    assert snap.values["scores"]  # 回答被评估：恢复后状态持续推进
    assert snap.values["question_count"] >= 1
