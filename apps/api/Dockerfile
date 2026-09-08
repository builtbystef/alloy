# The API, worker, and scheduler. One image; the deployment picks the command
# (see Deploying in the root README).
# Build from the repository root, where the uv workspace and lockfile live:
#
#   docker build --file apps/api/Dockerfile --tag alloy-api .

# --- Dependencies -------------------------------------------------------------
# The Python from .python-version, and uv copied in from its own image: the
# version must satisfy `required-version` in the root pyproject.toml.
FROM python:3.14-slim-bookworm AS build

COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Dependencies first, from the lockfile alone, so this layer survives source
# changes. The workspace member's pyproject.toml is needed for the resolution.
COPY pyproject.toml uv.lock ./
COPY apps/api/pyproject.toml apps/api/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-workspace --package alloy-api

# Then the project itself: source, migrations, and the Alembic and FastAPI
# config in apps/api. An editable install, so the venv points at /app/apps/api.
COPY apps/api apps/api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --package alloy-api

# --- Runtime ------------------------------------------------------------------
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

COPY --from=build --chown=app:app /app /app

# `fastapi run` and `alembic` read pyproject.toml from the working directory.
WORKDIR /app/apps/api
USER app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/', timeout=2)"]

# No reload, binds 0.0.0.0. `--proxy-headers` trusts X-Forwarded-* from the
# platform's network, where the web app's proxy route is the only caller.
CMD ["fastapi", "run", "--port", "8000", "--proxy-headers"]
