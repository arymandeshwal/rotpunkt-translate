from collections.abc import AsyncIterator
from typing import Any

from httpx import AsyncClient
from sqlalchemy.exc import OperationalError

from app.db import get_session
from app.main import app


async def test_health_ok_when_database_reachable(client: AsyncClient) -> None:
    response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_degraded_when_database_unreachable(client: AsyncClient) -> None:
    class BrokenSession:
        async def execute(self, *_: Any) -> None:
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    async def broken_session() -> AsyncIterator[BrokenSession]:
        yield BrokenSession()

    app.dependency_overrides[get_session] = broken_session

    response = await client.get("/api/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "database": "unavailable"}


async def test_openapi_schema_is_served(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
