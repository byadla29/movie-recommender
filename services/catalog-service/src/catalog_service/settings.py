"""Configuration from environment variables (12-factor).

Every value comes from the environment (or a git-ignored `.env` when running outside
Docker). `database_url` is a SecretStr so it is masked if settings are ever printed/logged.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

SERVICE_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    service_name: str = "catalog-service"
    environment: Literal["local", "test", "ci", "production"] = "local"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # e.g. postgresql+psycopg://catalog_svc:<password>@localhost:5433/catalog_db
    database_url: SecretStr
    db_connect_timeout_seconds: int = 2

    alembic_ini_path: Path = SERVICE_ROOT / "alembic.ini"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # values come from the environment
