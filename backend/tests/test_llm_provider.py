import pytest
from pydantic import BaseModel

from interview_agent.llm.provider import StubProvider, get_provider, reset_provider

pytestmark = [pytest.mark.integration]  # ledger 落库需要 PG


class _Eval(BaseModel):
    score: int
    rationale: str


async def test_stub_stream_yields_text():
    p = StubProvider()
    chunks = [c async for c in p.stream([{"role": "user", "content": "出题"}])]
    assert "".join(chunks)  # 非空可拼接


async def test_stub_structured_returns_valid_schema():
    p = StubProvider()
    out = await p.structured(_Eval, [{"role": "user", "content": "评估"}])
    assert 0 <= out.score <= 10 and out.rationale


async def test_ledger_row_written():
    import uuid

    p = StubProvider()
    node = f"test-{uuid.uuid4().hex[:8]}"  # 每次唯一：避免历史行导致 scalar_one 冲突
    await p.structured(_Eval, [{"role": "user", "content": "评估"}], session_id=None, node=node)
    from sqlalchemy import select

    from interview_agent.core.db import get_session_factory
    from interview_agent.core.models import CostLedger

    async with get_session_factory()() as s:
        row = (await s.execute(select(CostLedger).where(CostLedger.node == node))).scalar_one()
        assert row.provider == "stub" and float(row.cost_cny) == 0


def test_factory_defaults_to_stub_without_key(monkeypatch):
    from interview_agent.core.config import get_settings

    get_settings.cache_clear()
    reset_provider()
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("USE_STUB_LLM", "1")
    assert isinstance(get_provider(), StubProvider)
    reset_provider()
