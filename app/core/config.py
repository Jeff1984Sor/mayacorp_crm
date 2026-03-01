from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mayacorp CRM"
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8011, alias="APP_PORT")
    central_db_url: str | None = Field(default=None, alias="CENTRAL_DB_URL")
    bootstrap_jwt_secret: str = Field(default="dev-bootstrap-secret", alias="BOOTSTRAP_JWT_SECRET")

    @property
    def central_database_url(self) -> str:
        if self.central_db_url:
            return self.central_db_url
        return f"sqlite+pysqlite:///{(DATA_DIR / 'central_dev.db').as_posix()}"


settings = Settings()
