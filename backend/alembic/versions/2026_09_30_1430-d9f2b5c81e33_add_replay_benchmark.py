"""add replay kind and benchmark link

Revision ID: d9f2b5c81e33
Revises: c8e1a4b70d22
Create Date: 2026-09-30 14:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d9f2b5c81e33"
down_revision: str | Sequence[str] | None = "c8e1a4b70d22"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "replays",
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="AGENTS"),
    )
    op.add_column("replays", sa.Column("benchmark_replay_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_replays_benchmark_replay_id_replays"),
        "replays",
        "replays",
        ["benchmark_replay_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_replays_benchmark_replay_id_replays"), "replays", type_="foreignkey"
    )
    op.drop_column("replays", "benchmark_replay_id")
    op.drop_column("replays", "kind")
