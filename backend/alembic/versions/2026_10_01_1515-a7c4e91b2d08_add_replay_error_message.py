"""add replay error message

Revision ID: a7c4e91b2d08
Revises: f2b8d1e60c19
Create Date: 2026-10-01 15:15:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c4e91b2d08"
down_revision: str | Sequence[str] | None = "f2b8d1e60c19"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("replays", sa.Column("error_message", sa.String(length=2000), nullable=True))


def downgrade() -> None:
    op.drop_column("replays", "error_message")
