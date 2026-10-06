"""add sma and random replay links

Revision ID: d5e0f3b92c18
Revises: c4d9e2a81b07
Create Date: 2026-10-06 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5e0f3b92c18"
down_revision: str | Sequence[str] | None = "c4d9e2a81b07"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("replays", sa.Column("sma_replay_id", sa.Integer(), nullable=True))
    op.add_column("replays", sa.Column("random_replay_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_replays_sma_replay_id_replays"),
        "replays",
        "replays",
        ["sma_replay_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        op.f("fk_replays_random_replay_id_replays"),
        "replays",
        "replays",
        ["random_replay_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_replays_random_replay_id_replays"), "replays", type_="foreignkey")
    op.drop_constraint(op.f("fk_replays_sma_replay_id_replays"), "replays", type_="foreignkey")
    op.drop_column("replays", "random_replay_id")
    op.drop_column("replays", "sma_replay_id")
