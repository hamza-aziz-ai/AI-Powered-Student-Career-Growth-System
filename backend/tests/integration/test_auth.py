import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client: AsyncClient, email: str, password: str = "correcthorsebattery") -> None:
    resp = await client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "full_name": "Test Parent"},
    )
    assert resp.status_code == 201, resp.text


async def test_register_login_me_refresh_logout_round_trip(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)

    # register() logs the user in via cookies already; confirm /me works.
    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == unique_email

    # A fresh client (no cookies) must log in explicitly.
    client.cookies.clear()
    unauth = await client.get("/api/auth/me")
    assert unauth.status_code == 401

    login = await client.post("/api/auth/login", json={"email": unique_email, "password": "correcthorsebattery"})
    assert login.status_code == 200

    me_after_login = await client.get("/api/auth/me")
    assert me_after_login.status_code == 200

    refresh = await client.post("/api/auth/refresh")
    assert refresh.status_code == 200

    me_after_refresh = await client.get("/api/auth/me")
    assert me_after_refresh.status_code == 200

    logout = await client.post("/api/auth/logout")
    assert logout.status_code == 200

    me_after_logout = await client.get("/api/auth/me")
    assert me_after_logout.status_code == 401


async def test_register_duplicate_email_rejected(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    dup = await client.post(
        "/api/auth/register",
        json={"email": unique_email, "password": "anotherpassword1", "full_name": "Someone Else"},
    )
    assert dup.status_code == 409


async def test_login_wrong_password_rejected(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)
    client.cookies.clear()
    resp = await client.post("/api/auth/login", json={"email": unique_email, "password": "wrongpassword"})
    assert resp.status_code == 401


async def test_login_nonexistent_email_rejected(client: AsyncClient):
    resp = await client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever123"})
    assert resp.status_code == 401


async def test_refresh_without_cookie_rejected(client: AsyncClient):
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401


async def test_reused_refresh_token_revokes_session(client: AsyncClient, unique_email: str):
    await _register(client, unique_email)

    stale_refresh_cookie = client.cookies.get("refresh_token")
    assert stale_refresh_cookie is not None

    first_refresh = await client.post("/api/auth/refresh")
    assert first_refresh.status_code == 200

    # Replay the now-rotated-away token — this must be treated as possible theft
    # and reject the request, per the reuse-detection logic in auth_service.
    client.cookies.set("refresh_token", stale_refresh_cookie)
    replay = await client.post("/api/auth/refresh")
    assert replay.status_code == 401

    # The whole session family should now be revoked, so even the latest
    # legitimate refresh token no longer works.
    current_refresh_cookie = first_refresh.cookies.get("refresh_token")
    client.cookies.set("refresh_token", current_refresh_cookie)
    also_rejected = await client.post("/api/auth/refresh")
    assert also_rejected.status_code == 401
