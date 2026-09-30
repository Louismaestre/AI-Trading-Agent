"""create replays and attach equity points

Revision ID: c8e1a4b70d22
Revises: b7c4d2e91a10
Create Date: 2026-09-30 14:10:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c8e1a4b70d22"
down_revision: str | Sequence[str] | None = "b7c4d2e91a10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "replays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("decision_frequency", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("days_done", sa.Integer(), nullable=False),
        sa.Column("days_total", sa.Integer(), nullable=False),
        sa.Column("current_date", sa.Date(), nullable=True),
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
            ["portfolio_id"],
            ["portfolios.id"],
            name=op.f("fk_replays_portfolio_id_portfolios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_replays")),
    )
    op.alter_column("equity_points", "session_id", existing_type=sa.Integer(), nullable=True)
    op.add_column("equity_points", sa.Column("replay_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_equity_points_replay_id_replays"),
        "equity_points",
        "replays",
        ["replay_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_check_constraint(
        "one_owner",
        "equity_points",
        "(session_id IS NULL) != (replay_id IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("ck_equity_points_one_owner"), "equity_points", type_="check")
    op.drop_constraint(
        op.f("fk_equity_points_replay_id_replays"), "equity_points", type_="foreignkey"
    )
    op.drop_column("equity_points", "replay_id")
    op.alter_column("equity_points", "session_id", existing_type=sa.Integer(), nullable=False)
    op.drop_table("replays")
