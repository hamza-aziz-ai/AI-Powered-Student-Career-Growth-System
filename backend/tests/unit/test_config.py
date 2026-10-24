import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.main import _docs_urls


@pytest.mark.parametrize(
    "secret",
    [
        "change-me-in-.env-do-not-use-in-production",  # code default
        "replace-with-a-random-64-char-hex-secret",  # .env.example sample
        "",
        "   ",
        "too-short",
    ],
)
def test_weak_jwt_secret_rejected_outside_development(secret):
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(_env_file=None, environment="production", jwt_secret_key=secret)


def test_real_jwt_secret_accepted_outside_development():
    settings = Settings(_env_file=None, environment="production", jwt_secret_key="a" * 64)
    assert not settings.is_development


def test_default_jwt_secret_allowed_in_development():
    assert Settings(_env_file=None, environment="development").is_development


def test_docs_only_served_in_development():
    dev = Settings(_env_file=None, environment="development")
    prod = Settings(_env_file=None, environment="production", jwt_secret_key="a" * 64)
    assert _docs_urls(dev) == {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
    assert _docs_urls(prod) == {"docs_url": None, "redoc_url": None, "openapi_url": None}
