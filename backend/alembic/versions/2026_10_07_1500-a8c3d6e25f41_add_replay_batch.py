"""add replay batch id and repeat index

Revision ID: a8c3d6e25f41
Revises: f7a2b5d14e30
Create Date: 2026-10-07 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a8c3d6e25f41"
down_revision: str | Sequence[str] | None = "f7a2b5d14e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("replays", sa.Column("batch_id", sa.String(length=16), nullable=True))
    op.add_column("replays", sa.Column("repeat_index", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_replays_batch_id"), "replays", ["batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_replays_batch_id"), table_name="replays")
    op.drop_column("replays", "repeat_index")
    op.drop_column("replays", "batch_id")
