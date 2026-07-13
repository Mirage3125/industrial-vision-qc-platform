import os

os.environ["FVQL_DATABASE_URL"] = "sqlite:///:memory:"
os.environ["FVQL_LOG_FILE"] = "logs/test-backend.jsonl"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base
from backend.app.db.session import build_engine
from backend.app.main import app
from backend.app.models import domain  # noqa: F401


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db_session(tmp_path: object) -> Session:
    database_path = tmp_path / "domain-test.db"  # type: ignore[operator]
    test_engine = build_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine, expire_on_commit=False)
    with session_factory() as session:
        yield session
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()
