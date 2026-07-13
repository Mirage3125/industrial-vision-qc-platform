from pathlib import Path

import pytest
from sqlalchemy import text

from backend.app.core.config import Settings
from backend.app.db.session import build_engine


def test_settings_accept_environment_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FVQL_ENVIRONMENT", "test")
    settings = Settings(_env_file=None)

    assert settings.environment == "test"
    assert settings.api_prefix == "/api/v1"


def test_sqlite_engine_is_usable(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")

    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    engine.dispose()
