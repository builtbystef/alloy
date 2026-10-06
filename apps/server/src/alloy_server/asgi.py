"""The ASGI entry point for `fastapi run` and `fastapi dev`: the one place, with
the worker, where the API reads the environment. Everything else (tests, the
OpenAPI export) calls `create_app` with its own settings."""

from alloy_server.config import Settings
from alloy_server.main import create_app

app = create_app(Settings())
