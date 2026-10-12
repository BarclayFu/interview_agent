"""成本记账：每次 LLM 调用落一行 cost_ledger（spec §5.2）。

DeepSeek 官方价（随官网调整，改价只动这两行常量）：
  deepseek-chat:    输入 ¥2/1M tokens，输出 ¥8/1M
  deepseek-reasoner:输入 ¥4/1M tokens，输出 ¥16/1M
"""

import time
import uuid
from dataclasses import dataclass

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import CostLedger

PRICE_PER_1M: dict[str, tuple[float, float]] = {
    "deepseek-chat": (2.0, 8.0),
    "deepseek-reasoner": (4.0, 16.0),
    "stub": (0.0, 0.0),
}


@dataclass
class Usage:
    session_id: uuid.UUID | str | None
    node: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int

    @property
    def cost_cny(self) -> float:
        pin, pout = PRICE_PER_1M.get(self.model, (0.0, 0.0))
        return round((self.prompt_tokens * pin + self.completion_tokens * pout) / 1_000_000, 6)


async def record_usage(usage: Usage) -> None:
    async with get_session_factory()() as s:
        s.add(
            CostLedger(
                session_id=usage.session_id,
                node=usage.node,
                provider=usage.provider,
                model=usage.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                cost_cny=usage.cost_cny,
                latency_ms=usage.latency_ms,
            )
        )
        await s.commit()


def now_ms() -> float:
    return time.perf_counter() * 1000
