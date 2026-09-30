"""add live session kind and benchmark link

Revision ID: b7c4d2e91a10
Revises: e4f2a91c8d07
Create Date: 2026-09-29 15:48:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7c4d2e91a10"
down_revision: str | Sequence[str] | None = "e4f2a91c8d07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "live_sessions",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="AGENTS"),
    )
    op.add_column("live_sessions", sa.Column("benchmark_session_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_live_sessions_benchmark_session_id_live_sessions"),
        "live_sessions",
        "live_sessions",
        ["benchmark_session_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_live_sessions_benchmark_session_id_live_sessions"),
        "live_sessions",
        type_="foreignkey",
    )
    op.drop_column("live_sessions", "benchmark_session_id")
    op.drop_column("live_sessions", "kind")
