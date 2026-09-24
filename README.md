# Alloy

An opinionated template for web apps: TypeScript + Next.js in front, Python +
FastAPI behind. Extends [carbon-fiber](https://github.com/builtbystef/carbon-fiber).

| Concern    | TypeScript                                    | Python                          |
| ---------- | --------------------------------------------- | ------------------------------- |
| Packages   | pnpm via [Vite+](https://viteplus.dev) (`vp`) | [uv](https://docs.astral.sh/uv) |
| Format     | oxfmt (`vp check`)                            | Ruff                            |
| Lint       | oxlint (`vp check`)                           | Ruff                            |
| Type check | tsc (`vp check`)                              | [ty](https://docs.astral.sh/ty) |
| Tests      | Vitest (`vp test`)                            | pytest                          |

## Requirements

- Node ≥ 24, Python ≥ 3.14 (uv downloads it), uv ≥ 0.12
- Docker with Compose, for the local PostgreSQL and RustFS

## Commands

```sh
vp run check         # format + lint + typecheck, both languages (check:fix to apply fixes)
vp run test          # Vitest + pytest
vp run ci            # everything CI runs
vp run db:up         # PostgreSQL and RustFS in Docker
vp run db:migrate    # alembic upgrade head
vp run dev           # API, worker, and web together
vp run dev:api       # http://127.0.0.1:8000/docs
vp run dev:web       # http://localhost:3000
```

Run `vp config` once after cloning to activate the pre-commit hook.

## Layout

- `apps/server`: FastAPI app, Procrastinate worker, and the assistant agent (package `alloy_server`).
- `apps/web`: Next.js 16 front end (`@alloy/web`).
- `packages/api-client`: typed fetch client generated from the API's OpenAPI schema (`@alloy/api-client`).

New projects go in `apps/*`, `packages/*`, or `tools/*`. TypeScript projects
extend a preset from `tsconfig/` and take versions from the catalog in
`pnpm-workspace.yaml`. Python projects are listed under
`[tool.uv.workspace] members` in the root `pyproject.toml`.

## apps/server

A modular monolith. Each feature under `modules/` has `router.py`,
`schemas.py`, `models.py`, `service.py` (the work, raises `AppError`s), and
`dependencies.py`. There is no repository layer: the session is the unit of
work. The assistant's tools and the worker's jobs call the same service
functions the routes do. A module imports other modules only through their
`service`, `models`, and `dependencies`.

Settings come from `ALLOY_*` environment variables or a local `.env`; every
one is documented in `apps/server/.env.example`. Routes are documented at
`/docs`.

- **Errors and logs**: every response and log line carries `X-Request-ID`. Unhandled exceptions become a plain 500.
- **Database**: SQLAlchemy 2 async over psycopg 3, Alembic migrations (`cd apps/server && uv run alembic revision --autogenerate -m "..."`). Integration tests run against real PostgreSQL in a rolled-back transaction; a model change without a migration fails CI.
- **Auth**: opaque server-side sessions in an `HttpOnly` `__Host-session` cookie, Argon2id passwords, emailed links for verification, reset, and email change. Deleted accounts are purged after `ALLOY_ACCOUNT_DELETION_GRACE`.
- **Rate limits**: fixed-window counters in the database, 429 with `Retry-After`. The `Limit`s sit next to the routes that use them.
- **Workspaces**: every record belongs to a workspace; roles are owner, admin, member, viewer. Handlers take a `Can*` dependency (404 for non-members, 403 without the permission). Invitations are emailed links.
- **Email and storage**: ports in `integrations/`. Email is queued and sent by the worker (console mailer by default). Storage is S3-compatible (RustFS locally); uploads and downloads are presigned URLs, keys are `workspaces/{id}/...`.
- **Jobs**: [Procrastinate](https://procrastinate.readthedocs.io) on the app's PostgreSQL, no broker. Jobs are written on the handler's session, so they commit or roll back with the rows they are about. Tasks live in a `jobs.py` next to what they work on.
- **Assistant**: one [Pydantic AI](https://pydantic.dev/docs/ai/) agent over the CRM services. `ALLOY_OPENAI_API_KEY` turns it on. Reads run freely, single writes run at once, deletes and bulk calls pause for approval. Every model call is recorded in `model_calls`.
- **CRM**: the demo (contacts, companies, tasks, attachments, CSV imports, dashboard). Deletable as a unit.

## Deploying

One image per app, one command per process, settings from environment variables:

| Process  | Image         | Command                                   | Port |
| -------- | ------------- | ----------------------------------------- | ---- |
| `api`    | `apps/server` | `fastapi run --port 8000 --proxy-headers` | 8000 |
| `worker` | `apps/server` | `alloy-worker`                            | none |
| `web`    | `apps/web`    | `node apps/web/server.js`                 | 3000 |

Plus managed PostgreSQL and an S3-compatible bucket. Only `web` needs a
public address; it forwards `/api/*` to the API. Run `alembic upgrade head`
from `/app/apps/server` before new code starts. Health checks: `/health/`
(liveness), `/health/{db,storage}` (readiness).

```sh
ALLOY_DATABASE_URL=postgresql+psycopg://...
ALLOY_STORAGE_ENDPOINT_URL=... ALLOY_STORAGE_BUCKET=... ALLOY_STORAGE_ACCESS_KEY=... ALLOY_STORAGE_SECRET_KEY=...
ALLOY_STORAGE_PATH_STYLE=false                   # true for MinIO and RustFS
ALLOY_FRONTEND_URL=https://app.example.com       # links in emails
ALLOY_OPENAI_API_KEY=...                         # optional; empty turns the assistant off
API_URL=http://api.internal:8000                 # web only
CLIENT_IP_HEADER=x-forwarded-for                 # web only: the header the platform sets to the visitor's address
```

`.github/workflows/images.yml` builds `ghcr.io/<owner>/<repo>/{server,web}`
after CI passes on `main`.

## Supply-chain policy

New package versions are held back for 4 days before install (pnpm
`minimumReleaseAge`, uv `exclude-newer`), and Dependabot runs weekly with the
same cooldown. pnpm runs no dependency build scripts (`strictDepBuilds` with
an empty `allowBuilds`), blocks exotic sub-dependencies, and refuses trust
downgrades. CI uses least-privilege permissions, SHA-pinned actions, and
frozen lockfiles.

## License

[MIT](LICENSE) © builtbystef
