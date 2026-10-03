import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
from sqlalchemy.engine import URL, make_url

BACKEND_DIR = Path(__file__).resolve().parents[1]


def with_database(url: str | URL, name: str) -> URL:
    return make_url(url).set(database=name)


def render(url: URL) -> str:
    return url.render_as_string(hide_password=False)


def _asyncpg_dsn(url: URL) -> str:
    return render(url.set(drivername="postgresql"))


async def _recreate_database(url: URL) -> None:
    conn = await asyncpg.connect(_asyncpg_dsn(url.set(database="postgres")))
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{url.database}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{url.database}"')
    finally:
        await conn.close()


def recreate_database(url: URL) -> None:
    asyncio.run(_recreate_database(url))


def alembic(url: URL, *args: str) -> subprocess.CompletedProcess[str]:
    """Run an Alembic command in a subprocess against the given database."""
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": render(url)},
        capture_output=True,
        text=True,
        check=False,
    )
