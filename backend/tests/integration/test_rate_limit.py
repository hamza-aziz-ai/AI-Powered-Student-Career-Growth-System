import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_login_rate_limit_returns_429_after_threshold(client: AsyncClient, unique_email: str):
    # Register once so the account exists, then hammer /login past its 5/minute limit.
    await client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "correcthorsebattery", "full_name": "Test Parent"},
    )
    client.cookies.clear()

    statuses = []
    for _ in range(7):
        resp = await client.post("/api/auth/login", json={"email": unique_email, "password": "wrongpassword"})
        statuses.append(resp.status_code)

    assert 401 in statuses
    assert 429 in statuses


async def test_register_rate_limit_returns_429_after_threshold(client: AsyncClient):
    statuses = []
    for i in range(5):
        resp = await client.post(
            "/api/auth/register",
            json={"email": f"rl-test-{i}@example.com", "password": "correcthorsebattery", "full_name": "Test"},
        )
        statuses.append(resp.status_code)
        client.cookies.clear()

    assert 201 in statuses
    assert 429 in statuses
