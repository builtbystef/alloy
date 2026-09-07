from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import HttpUrl, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from alloy_api.mail import MailProvider


class Settings(BaseSettings):
    """Read from `ALLOY_*` environment variables and `.env`."""

    app_name: str = "Alloy API"

    cors_origins: list[str] = ["http://localhost:3000"]

    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://alloy:alloy@localhost:5432/alloy")
    # Log SQL queries to the console when enabled.
    database_echo: bool = False

    # Python logging level for the app's own loggers (the console mailer logs at INFO).
    log_level: str = "INFO"

    # How long a login stays valid. Env: seconds or ISO 8601 (`P30D`).
    session_ttl: timedelta = timedelta(days=30)
    # How long a workspace invitation link works.
    invite_ttl: timedelta = timedelta(days=7)

    # Where the web app lives; invitation links point here.
    frontend_url: HttpUrl = HttpUrl("http://localhost:3000")

    mail_provider: MailProvider = "console"
    mail_from: str = "Alloy <no-reply@alloy.local>"

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALLOY_")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
