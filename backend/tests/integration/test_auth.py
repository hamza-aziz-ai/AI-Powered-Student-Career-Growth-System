import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.refresh_token import RefreshToken
from app.schemas.user import UserRegister
from app.services import auth_service

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


async def test_failed_refresh_deletes_auth_cookies(client: AsyncClient):
    client.cookies.set("refresh_token", "not-a-real-token")
    resp = await client.post("/api/auth/refresh")
    assert resp.status_code == 401

    set_cookies = resp.headers.get_list("set-cookie")
    for name in ("access_token", "refresh_token"):
        header = next((h for h in set_cookies if h.startswith(f"{name}=")), None)
        assert header is not None, f"no Set-Cookie deleting {name}: {set_cookies}"
        assert "Max-Age=0" in header


def _session_maker_pausing_after(test_engine, method_name: str, barrier: asyncio.Barrier):
    """Sessions whose `method_name` call waits at `barrier` once it returns, so two
    concurrent callers are both past that point before either continues. That forces
    the overlap a plain asyncio.gather() only produces by chance."""

    class PausingSession(AsyncSession):
        pass

    async def paused(self, *args, **kwargs):
        result = await getattr(AsyncSession, method_name)(self, *args, **kwargs)
        await barrier.wait()
        return result

    setattr(PausingSession, method_name, paused)
    return async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=PausingSession)


async def test_concurrent_rotation_issues_exactly_one_successor(test_engine, db_session: AsyncSession, unique_email: str):
    user = await auth_service.register_user(
        db_session, UserRegister(email=unique_email, password="correcthorsebattery", full_name="Test Parent")
    )
    _, raw_refresh = await auth_service.issue_token_pair(db_session, user)

    # rotate_refresh_token calls session.get(User) between reading the token and
    # consuming it: pausing there makes both requests read it while still unrevoked,
    # so the loser goes through the atomic-consumption branch, not the revoked one.
    session_maker = _session_maker_pausing_after(test_engine, "get", asyncio.Barrier(2))

    async def rotate():
        async with session_maker() as session:
            try:
                return await auth_service.rotate_refresh_token(session, raw_refresh)
            except auth_service.InvalidRefreshTokenError:
                return None

    results = await asyncio.gather(rotate(), rotate())
    winners = [r for r in results if r is not None]
    assert len(winners) == 1

    # No branching: the original token plus exactly one successor. The loser counts as
    # reuse, so every refresh token for the user ends up revoked.
    token_count = await db_session.scalar(
        select(func.count()).select_from(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    live_count = await db_session.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    )
    assert token_count == 2
    assert live_count == 0


async def test_concurrent_duplicate_registration_maps_to_conflict(test_engine, db_session, unique_email: str):
    # db_session is requested only so its teardown deletes the rows created here.
    # register_user's only session.scalar() call is the "email taken?" pre-check:
    # pausing after it makes both requests pass the check, so the unique index decides.
    session_maker = _session_maker_pausing_after(test_engine, "scalar", asyncio.Barrier(2))
    data = UserRegister(email=unique_email, password="correcthorsebattery", full_name="Test Parent")

    async def register():
        async with session_maker() as session:
            try:
                return await auth_service.register_user(session, data)
            except auth_service.EmailAlreadyRegisteredError:
                return None

    results = await asyncio.gather(register(), register())
    assert sum(r is not None for r in results) == 1
