"""成本记账：每次 LLM 调用落一行 cost_ledger（spec §5.2）。

DeepSeek 官方价（随官网调整，改价只动这张表）：
  deepseek-chat:    cache 命中输入 ¥0.5/1M，未命中输入 ¥2/1M，输出 ¥8/1M
  deepseek-reasoner:cache 命中输入 ¥1/1M，  未命中输入 ¥4/1M，输出 ¥16/1M
未记录 cache 字段时（历史行/Stub），全部输入按未命中价计。
"""

import time
import uuid
from dataclasses import dataclass

from interview_agent.core.db import get_session_factory
from interview_agent.core.models import CostLedger

# model -> (cache_hit_input, cache_miss_input, output) 单位：元/1M tokens
PRICE_PER_1M: dict[str, tuple[float, float, float]] = {
    "deepseek-chat": (0.5, 2.0, 8.0),
    "deepseek-reasoner": (1.0, 4.0, 16.0),
    "stub": (0.0, 0.0, 0.0),
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
    cache_hit_tokens: int = 0
    cache_miss_tokens: int = 0

    @property
    def cost_cny(self) -> float:
        p_hit, p_miss, p_out = PRICE_PER_1M.get(self.model, (0.0, 0.0, 0.0))
        miss = self.cache_miss_tokens or max(self.prompt_tokens - self.cache_hit_tokens, 0)
        return round(
            (self.cache_hit_tokens * p_hit + miss * p_miss + self.completion_tokens * p_out)
            / 1_000_000,
            6,
        )


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
                cache_hit_tokens=usage.cache_hit_tokens,
                cache_miss_tokens=usage.cache_miss_tokens,
                cost_cny=usage.cost_cny,
                latency_ms=usage.latency_ms,
            )
        )
        await s.commit()


def now_ms() -> float:
    return time.perf_counter() * 1000
