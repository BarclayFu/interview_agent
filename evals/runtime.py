"""评测运行时的共享事件循环。

为什么不用 asyncio.run：langchain-openai 的客户端状态与首次使用的 loop 绑定，
跨 loop 复用会抛 "Event loop is closed"（已用裸 openai SDK 对照验证：问题在
langchain 层而非我们的代码）。生产是单个长驻 loop，评测也统一到一个 session 级
loop，行为一致且规避该问题。
"""

import asyncio
from collections.abc import Coroutine
from typing import Any, TypeVar

T = TypeVar("T")

_loop: asyncio.AbstractEventLoop | None = None


def get_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
    return _loop


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    return get_loop().run_until_complete(coro)
