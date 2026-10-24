import httpx
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.core.rate_limit import limiter
from app.db.session import get_db
from app.routers import auth, children, insights

settings = get_settings()
configure_logging()
logger = get_logger(__name__)


def _docs_urls(settings: Settings) -> dict:
    """Interactive docs and the OpenAPI schema are only exposed in development."""
    enabled = settings.is_development
    return {
        "docs_url": "/docs" if enabled else None,
        "redoc_url": "/redoc" if enabled else None,
        "openapi_url": "/openapi.json" if enabled else None,
    }


app = FastAPI(title="Career Growth AI for Kids API", **_docs_urls(settings))

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(children.router)
app.include_router(insights.router)


@app.get("/api/health")
async def health() -> dict:
    """Liveness: the process is up. Does not check dependencies — see /api/ready."""
    return {"status": "ok"}


async def _ollama_reachable() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.ollama_base_url}/api/version")
        return resp.status_code == 200
    except httpx.HTTPError:
        return False


@app.get("/api/ready")
async def ready(db: AsyncSession = Depends(get_db)) -> JSONResponse:
    """Readiness: PostgreSQL answers a query and the Ollama daemon is reachable."""
    try:
        await db.execute(text("SELECT 1"))
        database_ok = True
    except Exception as exc:
        logger.warning("readiness: database check failed: %s", type(exc).__name__)
        database_ok = False

    ollama_ok = await _ollama_reachable()
    checks = {"database": "ok" if database_ok else "unavailable", "ollama": "ok" if ollama_ok else "unavailable"}
    is_ready = database_ok and ollama_ok
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "checks": checks},
    )
