import uuid
from collections.abc import AsyncGenerator

import psycopg2
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Child, CareerInsight, RefreshToken, User  # noqa: F401

settings = get_settings()

# Run against a dedicated `<db>_test` database on the same Postgres instance —
# never against the dev database, and never mocked, per the plan's testing approach.
_TEST_DB_NAME = f"{settings.database_url.rsplit('/', 1)[-1]}_test"
_TEST_DATABASE_URL = settings.database_url.rsplit("/", 1)[0] + f"/{_TEST_DB_NAME}"
_MAINTENANCE_URL = settings.database_url.rsplit("/", 1)[0].replace("postgresql+asyncpg://", "postgresql://") + "/postgres"


def _ensure_test_database_exists() -> None:
    conn = psycopg2.connect(_MAINTENANCE_URL)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (_TEST_DB_NAME,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{_TEST_DB_NAME}"')
    finally:
        conn.close()


@pytest.fixture(scope="session")
def test_engine():
    _ensure_test_database_exists()
    engine = create_async_engine(_TEST_DATABASE_URL)
    yield engine


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _create_schema(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    session_maker = async_sessionmaker(bind=test_engine, expire_on_commit=False, class_=AsyncSession)
    async with session_maker() as session:
        yield session
        # Isolate tests by truncating everything touched, rather than relying on
        # rollback — the app code under test commits its own transactions.
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    # The ASGI test transport has no real client IP, so every unauthenticated
    # request (register/login) would otherwise share one rate-limit bucket
    # across tests. Reset it per-test so rate limiting doesn't leak between tests.
    app.state.limiter.reset()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def unique_email() -> str:
    return f"parent-{uuid.uuid4().hex[:12]}@example.com"
