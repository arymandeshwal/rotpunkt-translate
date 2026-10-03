"""Migrations run against their own throwaway database, separate from the shared test DB."""

import pytest
from sqlalchemy.engine import URL

from tests.conftest import TEST_DATABASE_URL
from tests.db_utils import alembic, recreate_database, with_database


@pytest.fixture(scope="module")
def migrations_db() -> URL:
    url = with_database(TEST_DATABASE_URL, f"{TEST_DATABASE_URL.database}_migrations")
    recreate_database(url)
    return url


def test_upgrade_downgrade_upgrade(migrations_db: URL) -> None:
    for step in (("upgrade", "head"), ("downgrade", "base"), ("upgrade", "head")):
        result = alembic(migrations_db, *step)
        assert result.returncode == 0, f"alembic {' '.join(step)} failed:\n{result.stderr}"


def test_models_match_migrations(migrations_db: URL) -> None:
    """Fails when a model changed without a matching migration."""
    alembic(migrations_db, "upgrade", "head")

    result = alembic(migrations_db, "check")

    assert result.returncode == 0, result.stdout + result.stderr
