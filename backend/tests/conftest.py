"""Provide shared backend test fixtures for the aiohttp test app and test database.

Edit this file when many backend tests need the same fixture or helper.
Copy fixture patterns here when you add another shared backend test helper.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from aiohttp.test_utils import TestClient

from backend.config import Settings
from backend.main import create_app


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    return Settings(
        mode="test",
        host="127.0.0.1",
        port=8081,
        db_path=tmp_path / "test.sqlite3",
        cookie_secret="test-secret",
        frontend_origin="http://127.0.0.1:5101",
    )


@pytest.fixture
async def app(test_settings: Settings):
    return create_app(test_settings)


@pytest.fixture
async def client(aiohttp_client, app) -> TestClient:
    return await aiohttp_client(app)


@pytest.fixture
async def db(app):
    return app["db"]


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Origin": "http://127.0.0.1:5101"}
