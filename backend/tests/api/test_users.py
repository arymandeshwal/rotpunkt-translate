import pytest
from httpx import AsyncClient
from app.models.user import Role
from app.services.auth import get_password_hash

@pytest.fixture
async def admin_user(db_session):
    from app.models.user import User
    user = User(
        email="admin_test@rotpunkt.de",
        hashed_password=get_password_hash("testpass"),
        role=Role.ADMIN
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.fixture
async def translator_user(db_session):
    from app.models.user import User
    user = User(
        email="translator_test@rotpunkt.de",
        hashed_password=get_password_hash("testpass"),
        role=Role.TRANSLATOR
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

async def test_login_success(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/auth/token",
        data={"username": "admin_test@rotpunkt.de", "password": "testpass"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

async def test_login_failure(client: AsyncClient, admin_user):
    response = await client.post(
        "/api/auth/token",
        data={"username": "admin_test@rotpunkt.de", "password": "wrongpass"}
    )
    assert response.status_code == 401

async def test_create_user_as_admin(client: AsyncClient, admin_user):
    # Login first
    login = await client.post("/api/auth/token", data={"username": "admin_test@rotpunkt.de", "password": "testpass"})
    token = login.json()["access_token"]
    
    response = await client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "new_user@rotpunkt.de", "password": "password123", "role": "reviewer"}
    )
    assert response.status_code == 201
    assert response.json()["email"] == "new_user@rotpunkt.de"
    assert response.json()["role"] == "reviewer"

async def test_create_user_as_translator_is_forbidden(client: AsyncClient, translator_user):
    login = await client.post("/api/auth/token", data={"username": "translator_test@rotpunkt.de", "password": "testpass"})
    token = login.json()["access_token"]
    
    response = await client.post(
        "/api/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "hacker@rotpunkt.de", "password": "hack", "role": "admin"}
    )
    assert response.status_code == 403
