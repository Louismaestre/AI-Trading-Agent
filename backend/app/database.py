"""PostgreSQL connection and base class for all tables."""

from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache

from sqlalchemy import DateTime, Engine, MetaData, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from app.config import get_settings

# Predictable constraint names, so Alembic generates stable migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampedModel(Base):
    """Adds an id and creation / update dates to every table."""

    __abstract__ = True

    # sort_order keeps `id` first and the dates last in the table.
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), sort_order=100
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), sort_order=100
    )


def build_engine(database_url: str) -> Engine:
    # Short timeout so the health check answers fast when the database is down.
    return create_engine(database_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})


@lru_cache
def get_engine() -> Engine:
    return build_engine(get_settings().database_url)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    with sessionmaker(get_engine(), expire_on_commit=False)() as session:
        yield session
