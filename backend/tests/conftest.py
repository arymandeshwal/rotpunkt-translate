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
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """API client whose requests share the test's rolled-back session."""

    async def test_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_session] = test_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
