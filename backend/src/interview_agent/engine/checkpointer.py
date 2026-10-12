"""AsyncPostgresSaver 装配（spec §5.4）。

- 连接要求：autocommit=True + row_factory=dict_row（AsyncPostgresSaver 硬性要求）。
- setup() 幂等（建 checkpoint 表），app 启动时调用一次。
- prod 走 Supavisor session 模式（spec §8）；psycopg 默认参数即可。
"""

from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import dict_row

from interview_agent.core.config import get_settings

_conn: Any = None
_saver: Any = None


def get_checkpointer() -> Any:
    if _saver is None:
        raise RuntimeError("checkpointer 未初始化：请先 await init_checkpointer()")
    return _saver


async def init_checkpointer() -> None:
    global _conn, _saver
    if _saver is not None:
        return
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    _conn = await AsyncConnection.connect(
        get_settings().database_url, autocommit=True, row_factory=dict_row
    )
    _saver = AsyncPostgresSaver(_conn)
    await _saver.setup()


async def close_checkpointer() -> None:
    global _conn, _saver
    if _conn is not None:
        await _conn.close()
    _conn = None
    _saver = None
