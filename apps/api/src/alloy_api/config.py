from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read from `ALLOY_*` environment variables and `.env`."""

    app_name: str = "Alloy API"
    cors_origins: list[str] = ["http://localhost:3000"]
    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://alloy:alloy@localhost:5432/alloy")
    database_echo: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALLOY_")


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
