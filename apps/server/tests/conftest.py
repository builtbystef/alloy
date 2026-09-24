"""Shared by `unit/` and `integration/`: the test database URL and the settings
fixture. Unit tests need neither PostgreSQL nor object storage; the integration
tree's own conftest adds the database, the app client, and the worker."""

import os
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.engine import make_url

from alloy_server.config import Settings, get_settings

if TYPE_CHECKING:
    from sqlalchemy.engine import URL

TEST_DATABASE = "alloy_test"
# The configured server (environment or `.env`), with the database swapped for the
# test one. Every `Settings(...)` a test builds picks this up from the environment.
_configured_url = make_url(str(Settings().database_url))
os.environ["ALLOY_DATABASE_URL"] = _configured_url.set(database=TEST_DATABASE).render_as_string(
    hide_password=False
)
get_settings.cache_clear()


@pytest.fixture(scope="session")
def configured_url() -> URL:
    """The development server, for creating the test database."""
    return _configured_url


@pytest.fixture
def settings() -> Settings:
    # No OpenAI key, whatever a local `.env` says: tests never call the model.
    return Settings(app_name="Test API", openai_api_key=None)
