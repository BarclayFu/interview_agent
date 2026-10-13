"""Alembic 环境：连接串从应用 Settings 注入（而非 alembic.ini），全异步。"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from interview_agent.core.config import get_settings
from interview_agent.core.db import async_url
from interview_agent.core.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    def include_object(obj, name, type_, reflected, compare_to):  # type: ignore[no-untyped-def]
        # LangGraph checkpointer 表由其自身管理（saver.setup()），不归 Alembic；
        # 若不排除，autogenerate 会把它们当成「多余的表」生成 drop，十分危险。
        is_checkpoint = type_ == "table" and (name or "").startswith("checkpoint")
        return not is_checkpoint

    context.configure(
        connection=connection, target_metadata=target_metadata, include_object=include_object
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_async_engine(async_url(get_settings().database_url))
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=async_url(get_settings().database_url),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_async_migrations())
