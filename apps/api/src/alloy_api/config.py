from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field, HttpUrl, PostgresDsn, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from alloy_api.jobs import JobsBroker
from alloy_api.mail import MailProvider
from alloy_api.ratelimit import RateLimitStore
from alloy_api.storage import StorageProvider


class Settings(BaseSettings):
    """Read from `ALLOY_*` environment variables and `.env`. `.env.example` documents
    every field."""

    app_name: str = "Alloy API"

    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://alloy:alloy@localhost:5432/alloy")
    database_echo: bool = False

    log_level: str = "INFO"

    logfire_token: SecretStr | None = None
    logfire_environment: str = "development"

    session_ttl: timedelta = timedelta(days=30)
    invite_ttl: timedelta = timedelta(days=7)
    verification_ttl: timedelta = timedelta(days=1)
    password_reset_ttl: timedelta = timedelta(hours=1)
    email_change_ttl: timedelta = timedelta(days=1)

    account_deletion_grace: timedelta = timedelta(days=7)

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
    import_max_bytes: int = Field(10 * 1024 * 1024, ge=1)

    jobs_broker: JobsBroker = "redis"
    redis_url: RedisDsn = RedisDsn("redis://localhost:6379/0")

    rate_limit_store: RateLimitStore = "redis"

    purge_after: timedelta = timedelta(days=7)

    # env_ignore_empty: hosting platforms often pass an unset variable as "",
    # which must read as the default (None for the Logfire token), not as "".
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALLOY_", env_ignore_empty=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
