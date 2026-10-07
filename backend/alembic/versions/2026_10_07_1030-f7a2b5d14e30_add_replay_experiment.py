"""add replay experiment id and graph snapshot

Revision ID: f7a2b5d14e30
Revises: e6f1a4c03d29
Create Date: 2026-10-07 10:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f7a2b5d14e30"
down_revision: str | Sequence[str] | None = "e6f1a4c03d29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("replays", sa.Column("experiment_id", sa.String(length=16), nullable=True))
    op.add_column("replays", sa.Column("graph", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("replays", "graph")
    op.drop_column("replays", "experiment_id")
