import pytest
from httpx import AsyncClient

from app import main
from app.db.session import get_db

pytestmark = pytest.mark.asyncio


async def test_health_is_liveness_only(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


async def test_ready_when_database_and_ollama_respond(client: AsyncClient, monkeypatch):
    async def reachable() -> bool:
        return True

    monkeypatch.setattr(main, "_ollama_reachable", reachable)
    resp = await client.get("/api/ready")
    assert resp.status_code == 200
    assert resp.json()["checks"] == {"database": "ok", "ollama": "ok"}


async def test_not_ready_when_ollama_is_down(client: AsyncClient, monkeypatch):
    async def unreachable() -> bool:
        return False

    monkeypatch.setattr(main, "_ollama_reachable", unreachable)
    resp = await client.get("/api/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"]["ollama"] == "unavailable"


async def test_not_ready_when_database_fails(client: AsyncClient, monkeypatch):
    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionRefusedError("database down")

    async def broken_db():
        yield BrokenSession()

    async def reachable() -> bool:
        return True

    monkeypatch.setattr(main, "_ollama_reachable", reachable)
    main.app.dependency_overrides[get_db] = broken_db
    resp = await client.get("/api/ready")
    assert resp.status_code == 503
    assert resp.json()["checks"] == {"database": "unavailable", "ollama": "ok"}
