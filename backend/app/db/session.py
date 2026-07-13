from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings


def build_engine(database_url: str) -> Engine:
    """Create an engine with SQLite-specific thread handling when required."""

    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    kwargs = {"poolclass": StaticPool} if database_url == "sqlite:///:memory:" else {}
    return create_engine(database_url, pool_pre_ping=True, connect_args=connect_args, **kwargs)


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """Provide a transaction-safe request session."""

    with SessionLocal() as session:
        yield session
