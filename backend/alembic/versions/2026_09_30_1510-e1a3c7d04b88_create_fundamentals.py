"""create fundamentals

Revision ID: e1a3c7d04b88
Revises: d9f2b5c81e33
Create Date: 2026-09-30 15:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1a3c7d04b88"
down_revision: str | Sequence[str] | None = "d9f2b5c81e33"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fundamentals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("revenue", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("gross_profit", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("operating_income", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("net_income", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("diluted_eps", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("total_debt", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("total_equity", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column("operating_cash_flow", sa.Numeric(precision=20, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["instrument_id"],
            ["instruments.id"],
            name=op.f("fk_fundamentals_instrument_id_instruments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fundamentals")),
        sa.UniqueConstraint(
            "instrument_id", "period_end", name=op.f("uq_fundamentals_instrument_id")
        ),
    )


def downgrade() -> None:
    op.drop_table("fundamentals")
