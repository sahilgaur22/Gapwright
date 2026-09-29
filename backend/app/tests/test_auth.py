from collections.abc import AsyncGenerator
from typing import Annotated

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.deps import require_role
from app.db.base import Base
from app.db.models.user import User
from app.db.session import get_db
from app.main import app


@pytest.fixture
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def client(test_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield test_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient) -> None:
    payload = {
        "email": "testuser@example.com",
        "password": "securepassword123",
        "role": "student",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "testuser@example.com"
    assert data["role"] == "student"
    assert "id" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    payload = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "role": "educator",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already exists" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_login_flow(client: AsyncClient) -> None:
    # 1. Register
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "mypassword123",
        "role": "educator",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    # 2. Login with wrong password
    wrong_login = {
        "email": "loginuser@example.com",
        "password": "wrongpassword",
    }
    res_wrong = await client.post("/api/v1/auth/login", json=wrong_login)
    assert res_wrong.status_code == 401
    assert "Incorrect email or password" in res_wrong.json()["detail"]

    # 3. Login with nonexistent email
    no_user_login = {
        "email": "nonexistent@example.com",
        "password": "mypassword123",
    }
    res_no_user = await client.post("/api/v1/auth/login", json=no_user_login)
    assert res_no_user.status_code == 401

    # 4. Login with correct password
    correct_login = {
        "email": "loginuser@example.com",
        "password": "mypassword123",
    }
    res_ok = await client.post("/api/v1/auth/login", json=correct_login)
    assert res_ok.status_code == 200
    token_data = res_ok.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_protected_me_endpoint(client: AsyncClient) -> None:
    # Register & Login
    user_payload = {
        "email": "authme@example.com",
        "password": "validpassword",
        "role": "student",
    }
    await client.post("/api/v1/auth/register", json=user_payload)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "authme@example.com", "password": "validpassword"},
    )
    token = login_res.json()["access_token"]

    # Unauthenticated request -> 401
    unauth_res = await client.get("/api/v1/auth/me")
    assert unauth_res.status_code == 401

    # Invalid token -> 401
    invalid_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer badtoken"}
    )
    assert invalid_res.status_code == 401

    # Valid token -> 200
    auth_res = await client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert auth_res.status_code == 200
    me_data = auth_res.json()
    assert me_data["email"] == "authme@example.com"
    assert me_data["role"] == "student"


@pytest.mark.asyncio
async def test_role_guard_dependency(client: AsyncClient) -> None:
    # Add a temporary test endpoint requiring admin role
    admin_guard = require_role("admin")

    @app.get("/test-admin-only")
    async def admin_route(
        _user: Annotated[User, Depends(admin_guard)],
    ) -> dict[str, str]:
        return {"status": "admin_granted"}

    # 1. Register student
    reg_student = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert reg_student.status_code == 201
    login_student = await client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert login_student.status_code == 200
    student_token = login_student.json()["access_token"]

    # Student accessing admin route -> 403 Forbidden
    forbidden_res = await client.get(
        "/test-admin-only",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert forbidden_res.status_code == 403
    assert "Access forbidden" in forbidden_res.json()["detail"]

    # 2. Register admin
    reg_admin = await client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "password123", "role": "admin"},
    )
    assert reg_admin.status_code == 201
    login_admin = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert login_admin.status_code == 200
    admin_token = login_admin.json()["access_token"]

    # Admin accessing admin route -> 200 OK
    admin_res = await client.get(
        "/test-admin-only",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_res.status_code == 200
    assert admin_res.json()["status"] == "admin_granted"
