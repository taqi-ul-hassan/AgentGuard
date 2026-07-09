"""SQLAlchemy database initialization and session management."""

from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


settings = get_settings()


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)


def init_database() -> None:
    """Initialize database tables for local and containerized deployments."""
    from app.storage import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_columns()


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it after use."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _ensure_sqlite_columns() -> None:
    """Add scaffold-era SQLite columns when running without Alembic migrations."""
    if not settings.database_url.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "audits" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("audits")}
    statements = []
    if "policy_results_json" not in existing:
        statements.append("ALTER TABLE audits ADD COLUMN policy_results_json JSON NOT NULL DEFAULT '[]'")
    if "model_metadata_json" not in existing:
        statements.append("ALTER TABLE audits ADD COLUMN model_metadata_json JSON NOT NULL DEFAULT '{}'")
    if not statements:
        return
    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
