"""共通フィクスチャ。"""
from __future__ import annotations

from pathlib import Path

import pytest

from app import create_app


@pytest.fixture()
def app(tmp_path: Path):
    db_path = tmp_path / "test.sqlite3"
    application = create_app({"DATABASE": str(db_path), "TESTING": True})
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
