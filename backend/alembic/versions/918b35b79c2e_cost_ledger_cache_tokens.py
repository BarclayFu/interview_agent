"""cost_ledger cache tokens

Revision ID: 918b35b79c2e
Revises: 75d1bb5fdc9a
Create Date: 2026-10-13 ...

注意：本文件由 autogenerate 生成后人工修正——删掉了对 checkpoint_* 表的 drop
（那些表由 LangGraph AsyncPostgresSaver 自管，不属于本迁移；env.py 已加 include_object 排除）。
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "918b35b79c2e"
down_revision: str | Sequence[str] | None = "75d1bb5fdc9a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # server_default：对已有行补齐非空列（存量报价按未命中价计，语义正确）
    op.add_column(
        "cost_ledger",
        sa.Column("cache_hit_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "cost_ledger",
        sa.Column("cache_miss_tokens", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("cost_ledger", "cache_miss_tokens")
    op.drop_column("cost_ledger", "cache_hit_tokens")
