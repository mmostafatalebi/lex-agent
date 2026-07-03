"""Database engine, session management, and ORM models.

The clause-examples taxonomy is stored in PostgreSQL with pgvector. This module
owns the SQLAlchemy engine, a transactional session scope, and the declarative
model that mirrors the ``clause_examples`` table.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from functools import lru_cache

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Engine,
    String,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from lexagent.config import settings

EMBEDDING_DIM = 1024


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when database access is attempted without ``DATABASE_URL`` set."""


class Base(DeclarativeBase):
    pass


class ClauseExample(Base):
    __tablename__ = "clause_examples"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    clause_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String, nullable=False)
    is_risky: Mapped[bool] = mapped_column(Boolean, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


def _normalize_url(url: str) -> str:
    """Route bare ``postgresql://`` URLs through the psycopg 3 driver."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return a cached SQLAlchemy engine built from ``settings.database_url``."""
    if not settings.database_url:
        raise DatabaseNotConfiguredError("DATABASE_URL is not set")
    return create_engine(_normalize_url(settings.database_url), pool_pre_ping=True)


@lru_cache(maxsize=1)
def _get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Yield a session, committing on success and rolling back on error."""
    session = _get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_extension(engine: Engine) -> None:
    """Create the pgvector extension if it does not already exist."""
    with engine.begin() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
