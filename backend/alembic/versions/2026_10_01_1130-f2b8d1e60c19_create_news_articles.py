"""create news articles

Revision ID: f2b8d1e60c19
Revises: e1a3c7d04b88
Create Date: 2026-10-01 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f2b8d1e60c19"
down_revision: str | Sequence[str] | None = "e1a3c7d04b88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_articles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("summary", sa.String(length=2000), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
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
            name=op.f("fk_news_articles_instrument_id_instruments"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_news_articles")),
        sa.UniqueConstraint("instrument_id", "url", name=op.f("uq_news_articles_instrument_id")),
    )
    op.create_index(
        "ix_news_articles_instrument_id_published_at",
        "news_articles",
        ["instrument_id", "published_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_news_articles_instrument_id_published_at", table_name="news_articles")
    op.drop_table("news_articles")
