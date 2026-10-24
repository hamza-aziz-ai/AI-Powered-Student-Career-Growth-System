from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_JWT_SECRET = "change-me-in-.env-do-not-use-in-production"
# The default above plus the sample value shipped in .env.example.
_PLACEHOLDER_JWT_SECRETS = {_DEFAULT_JWT_SECRET, "replace-with-a-random-64-char-hex-secret"}
_MIN_JWT_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../.env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/career_growth"

    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:120b-cloud"
    ollama_timeout_seconds: float = 90.0

    allowed_origins: str = "http://localhost:5173"

    @model_validator(mode="after")
    def _reject_weak_secret_outside_development(self) -> "Settings":
        if self.is_development:
            return self
        secret = self.jwt_secret_key.strip()
        if secret in _PLACEHOLDER_JWT_SECRETS or len(secret) < _MIN_JWT_SECRET_LENGTH:
            raise ValueError(
                f"JWT_SECRET_KEY must be a real random secret of at least {_MIN_JWT_SECRET_LENGTH} characters "
                "when ENVIRONMENT is not development"
            )
        return self

    @property
    def is_development(self) -> bool:
        return self.environment == "development"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
