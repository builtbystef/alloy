from datetime import timedelta
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from pydantic import Field, HttpUrl, PostgresDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from alloy_server.integrations.ai import AIProvider, ReasoningEffort
from alloy_server.integrations.mail import MailProvider
from alloy_server.integrations.storage import StorageProvider
from alloy_server.shared.logs import LogFormat


class Settings(BaseSettings):
    """Read from `ALLOY_*` environment variables and `.env`. `.env.example` documents
    every field."""

    # --- App ---
    app_name: str = "Alloy API"
    log_level: str = "INFO"
    # "text" for a terminal, "json" for a log collector.
    log_format: LogFormat = "text"
    # Logfire write token. None: telemetry is off.
    logfire_token: SecretStr | None = None
    # Shown in Logfire to tell deployments apart.
    logfire_environment: str = "development"
    # Where links in emails point.
    frontend_url: HttpUrl = HttpUrl("http://localhost:3000")

    # --- Database ---
    database_url: PostgresDsn = PostgresDsn("postgresql+psycopg://alloy:alloy@localhost:5432/alloy")
    database_echo: bool = False
    database_pool_size: int = Field(5, ge=1)
    database_max_overflow: int = Field(10, ge=0)
    # PostgreSQL cancels any statement that runs longer than this.
    database_statement_timeout: timedelta = timedelta(seconds=30)

    # --- Sessions and tokens ---
    session_ttl: timedelta = timedelta(days=30)
    invite_ttl: timedelta = timedelta(days=7)
    verification_ttl: timedelta = timedelta(days=1)
    password_reset_ttl: timedelta = timedelta(hours=1)
    email_change_ttl: timedelta = timedelta(days=1)
    # How long a deleted account can still be brought back by logging in.
    account_deletion_grace: timedelta = timedelta(days=7)

    # --- Email ---
    # "console" logs each message instead of sending it.
    mail_provider: MailProvider = "console"
    mail_from: str = "Alloy <no-reply@alloy.local>"

    # --- Object storage ---
    # "s3" covers every S3-compatible service.
    storage_provider: StorageProvider = "s3"
    storage_bucket: str = "alloy"
    # None for AWS S3 itself.
    storage_endpoint_url: HttpUrl | None = HttpUrl("http://127.0.0.1:9000")
    # Where the browser reaches storage, when that differs from the endpoint above.
    storage_public_endpoint_url: HttpUrl | None = None
    storage_region: str = "us-east-1"
    storage_access_key: str = "rustfsadmin"
    storage_secret_key: SecretStr = SecretStr("rustfsadmin")
    # True: host/bucket/key URLs (RustFS, MinIO). False: bucket.host/key (AWS).
    storage_path_style: bool = True
    storage_url_ttl: timedelta = timedelta(minutes=15)

    # --- Attachments and imports ---
    attachment_max_bytes: int = Field(25 * 1024 * 1024, ge=1)
    import_max_bytes: int = Field(10 * 1024 * 1024, ge=1)

    # --- Background jobs ---
    # Jobs one worker process runs at a time.
    jobs_concurrency: int = Field(2, ge=1)
    # How long revoked logins, used invitations, and abandoned uploads stay before purge.
    purge_after: timedelta = timedelta(days=7)
    # An import still queued or running after this is marked failed by the purge job.
    import_timeout: timedelta = timedelta(hours=1)

    # --- AI ---
    # "openai" addresses the model through the Responses API.
    ai_provider: AIProvider = "openai"
    # The key behind the assistant. None: the assistant endpoints answer 503.
    openai_api_key: SecretStr | None = None
    ai_model: str = "gpt-5.6-luna"
    ai_reasoning_effort: ReasoningEffort = "low"

    # --- Assistant ---
    # Images and PDFs in the chat are shown to the model up to this size; bigger files by name only.
    assistant_file_read_max_bytes: int = Field(4 * 1024 * 1024, ge=1)
    # A file dropped into the chat but never attached to a record is removed after this.
    chat_upload_ttl: timedelta = timedelta(days=1)

    # env_ignore_empty: hosting platforms often pass an unset variable as "",
    # which must read as the default (None for the Logfire token), not as "".
    model_config = SettingsConfigDict(env_file=".env", env_prefix="ALLOY_", env_ignore_empty=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


SettingsDep = Annotated[Settings, Depends(get_settings)]
