"""全局测试约束：强制 StubProvider（确定性 + 零成本）。

本地 .env 配有真实 DEEPSEEK_API_KEY 时，业务代码默认会走 DeepSeekProvider；
测试必须与此解耦，否则输出不确定且产生真实费用。真实 LLM 的验证属于评测门禁（evals/）的职责。
"""

import pytest

from interview_agent.core.config import get_settings
from interview_agent.llm.provider import reset_provider


@pytest.fixture(autouse=True)
def _force_stub_llm(monkeypatch):
    monkeypatch.setenv("USE_STUB_LLM", "1")
    get_settings.cache_clear()
    reset_provider()
    yield
    reset_provider()
    get_settings.cache_clear()
