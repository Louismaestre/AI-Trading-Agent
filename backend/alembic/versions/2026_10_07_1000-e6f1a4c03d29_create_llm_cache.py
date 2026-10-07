"""create llm cache

Revision ID: e6f1a4c03d29
Revises: d5e0f3b92c18
Create Date: 2026-10-07 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e6f1a4c03d29"
down_revision: str | Sequence[str] | None = "d5e0f3b92c18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "llm_cache",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cache_key", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("schema_name", sa.String(length=100), nullable=False),
        sa.Column("response", JSONB(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_llm_cache")),
        sa.UniqueConstraint("cache_key", name=op.f("uq_llm_cache_cache_key")),
    )


def downgrade() -> None:
    op.drop_table("llm_cache")
