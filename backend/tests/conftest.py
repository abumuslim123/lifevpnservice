"""
Общие фикстуры для тестов.

Стратегия БД:
  - DATABASE_URL переопределяется через os.environ ДО любых импортов из app.*
  - create_async_engine мокируется, чтобы обойти PostgreSQL-параметры
    pool_size/max_overflow, несовместимые с SQLite (NullPool)
  - Все тесты работают с SQLite (aiosqlite), не требуя запущенной PostgreSQL
"""
from __future__ import annotations

import os
from unittest.mock import patch

# 1. Подменяем DATABASE_URL — pydantic-settings читает env при Settings()
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test_vpnservice.db"
)
os.environ["DATABASE_SYNC_URL"] = "sqlite:///./test_vpnservice.db"

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# 2. Создаём SQLite-движок ДО импорта app.database
_TEST_DB_URL = os.environ["DATABASE_URL"]
_test_engine = create_async_engine(
    _TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 3. Мокируем create_async_engine при импорте app.database — возвращаем
#    уже созданный test_engine, игнорируя pool_size/max_overflow из database.py
with patch(
    "sqlalchemy.ext.asyncio.create_async_engine",
    return_value=_test_engine,
):
    import app.database as _db_module  # noqa: E402

# 4. Заменяем AsyncSessionLocal, чтобы background-функции тоже шли в SQLite
_db_module.AsyncSessionLocal = _TestSession

from app.main import app  # noqa: E402 — импортируем после патча
from app.database import get_db  # noqa: E402


async def _override_get_db():
    async with _TestSession() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Фикстуры
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def client():
    """TestClient с запущенным lifespan (создаёт таблицы + admin-пользователя)."""
    from starlette.testclient import TestClient
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def auth_headers(client):
    """Bearer-заголовок для admin-пользователя."""
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200, f"Не удалось войти: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def server_payload():
    """Минимальный payload для создания сервера."""
    return {
        "name": "Test Server",
        "ip_address": "10.0.0.1",
        "ssh_port": 22,
        "ssh_user": "root",
        "ssh_password": "secret",
        "os_type": "ubuntu",
    }


@pytest.fixture()
def client_payload():
    """Минимальный payload для создания клиента."""
    return {"name": "Test Client", "email": "test@example.com"}
