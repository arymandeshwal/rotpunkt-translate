import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from tests.db_utils import alembic, recreate_database, render, with_database

# Point the app at a dedicated test database before anything creates an engine.
_dev_url = make_url(Settings().database_url)
TEST_DATABASE_URL = with_database(_dev_url, f"{_dev_url.database}_test")
os.environ["DATABASE_URL"] = render(TEST_DATABASE_URL)

from app.db import engine, get_session  # noqa: E402
from app.main import app  # noqa: E402
from app.api.dependencies import get_current_user  # noqa: E402
from app.models.user import User, Role  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database() -> None:
    """Create a fresh test database and migrate it to the latest revision."""
    recreate_database(TEST_DATABASE_URL)
    result = alembic(TEST_DATABASE_URL, "upgrade", "head")
    assert result.returncode == 0, result.stderr


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """A session whose changes are rolled back after the test, even if it commits."""
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(
            bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
def current_user_override():
    """Provides a default admin user for tests that don't need specific auth testing."""
    return User(email="test@example.com", role=Role.ADMIN, is_active=True, hashed_password="fake")

@pytest.fixture
async def client(db_session: AsyncSession, current_user_override) -> AsyncIterator[AsyncClient]:
    """API client whose requests share the test's rolled-back session and bypass auth by default."""

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    async def override_get_current_user():
        return current_user_override

    app.dependency_overrides[get_session] = test_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
