"""add decision trace

Revision ID: c4d9e2a81b07
Revises: a7c4e91b2d08
Create Date: 2026-10-06 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "c4d9e2a81b07"
down_revision: str | Sequence[str] | None = "a7c4e91b2d08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("agent_decisions", sa.Column("reports", JSONB(), nullable=True))
    op.add_column("agent_decisions", sa.Column("debate", JSONB(), nullable=True))
    op.add_column("agent_decisions", sa.Column("risk", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_decisions", "risk")
    op.drop_column("agent_decisions", "debate")
    op.drop_column("agent_decisions", "reports")
