from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from alloy_api.mail import MailProvider
from alloy_api.storage import StorageProvider


class Settings(BaseSettings):
    """Read from `ALLOY_*` environment variables and `.env`. `.env.example` documents
    every field."""

    app_name: str = "Alloy API"

    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://alloy:alloy@localhost:5432/alloy")
    database_echo: bool = False

    log_level: str = "INFO"

    session_ttl: timedelta = timedelta(days=30)
    invite_ttl: timedelta = timedelta(days=7)
    verification_ttl: timedelta = timedelta(days=1)

    frontend_url: HttpUrl = HttpUrl("http://localhost:3000")

    mail_provider: MailProvider = "console"
    mail_from: str = "Alloy <no-reply@alloy.local>"

    storage_provider: StorageProvider = "s3"
    storage_bucket: str = "alloy"
    storage_endpoint_url: HttpUrl | None = HttpUrl("http://127.0.0.1:9000")
    storage_public_endpoint_url: HttpUrl | None = None
    storage_region: str = "us-east-1"
    storage_access_key: str = "rustfsadmin"
    storage_secret_key: SecretStr = SecretStr("rustfsadmin")
    storage_path_style: bool = True
    storage_url_ttl: timedelta = timedelta(minutes=15)

    attachment_max_bytes: int = Field(25 * 1024 * 1024, ge=1)

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALLOY_")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
