"""Configuration from environment variables (12-factor).

Every value comes from the environment (or a git-ignored `.env` when running outside
Docker). `database_url` is a SecretStr so it is masked if settings are ever printed/logged.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "user-service"
    environment: Literal["local", "test", "ci", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # e.g. postgresql+psycopg://user_svc:<password>@localhost:5433/user_db
    database_url: SecretStr
    db_connect_timeout_seconds: int = 2

    alembic_ini_path: Path = SERVICE_ROOT / "alembic.ini"

    # --- Authentication: verifying identity-provider tokens (JWTs) ---
    # Who issues our tokens, e.g. https://<your-app>.clerk.accounts.dev. Unset = protected
    # endpoints answer 503 "authentication not configured" (fail closed, never open).
    auth_issuer: str | None = None
    # Where the issuer publishes its public keys. Default: <issuer>/.well-known/jwks.json
    auth_jwks_url: str | None = None
    # Optional extra checks. Set when the provider puts them in the token.
    auth_audience: str | None = None  # required "aud" claim value
    auth_authorized_parties: list[str] = []  # allowed "azp" values (frontend origins)
    auth_clock_skew_seconds: int = 5  # tolerance for clocks that differ slightly
    auth_jwks_timeout_seconds: float = 3.0

    @field_validator("auth_issuer", "auth_jwks_url", "auth_audience", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        """Treat `AUTH_ISSUER=` (empty) the same as not setting it."""
        return None if isinstance(value, str) and not value.strip() else value

    @property
    def resolved_jwks_url(self) -> str | None:
        if self.auth_jwks_url:
            return self.auth_jwks_url
        if self.auth_issuer:
            return self.auth_issuer.rstrip("/") + "/.well-known/jwks.json"
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
