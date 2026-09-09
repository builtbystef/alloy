# Alloy

An opinionated template for creating web apps using Typescript + Next.js and Python + FastAPI.

Extending carbon-fiber template (https://github.com/builtbystef/carbon-fiber)

A template for any kind of project: apps, libraries, CLIs, services, in
TypeScript, Python, or both. Each language has one toolchain that handles
dependencies, formatting, linting, type checking, and tests:

| Concern    | TypeScript                                    | Python                          |
| ---------- | --------------------------------------------- | ------------------------------- |
| Packages   | pnpm via [Vite+](https://viteplus.dev) (`vp`) | [uv](https://docs.astral.sh/uv) |
| Format     | oxfmt (`vp check`)                            | Ruff (`ruff format`)            |
| Lint       | oxlint (`vp check`)                           | Ruff (`ruff check`)             |
| Type check | tsc (`vp check`)                              | [ty](https://docs.astral.sh/ty) |
| Tests      | Vitest (`vp test`)                            | pytest                          |
| Config     | `vite.config.ts`, `tsconfig/`                 | `pyproject.toml`                |

## Requirements

- Node ≥ 24 (pinned in `.node-version`, enforced at install)
- Python ≥ 3.14 (pinned in `.python-version`; uv downloads it on demand)
- uv ≥ 0.12 (`required-version` in `pyproject.toml`)
- Docker with Compose, for the local PostgreSQL, Redis, and RustFS object
  storage that `apps/api` and its tests use

## Commands

The root `package.json` scripts cover both languages:

```sh
vp run check        # format + lint + typecheck, both languages
vp run check:fix
vp run test         # Vitest + pytest
vp run build
vp run ci           # everything CI runs
vp run db:up        # PostgreSQL, Redis, and RustFS in Docker, waits until they accept connections
vp run db:migrate   # apply pending Alembic migrations
vp run db:down      # stop PostgreSQL (data is kept; add --volumes to wipe it)
vp run dev:api      # FastAPI with reload, http://127.0.0.1:8000
vp run dev:worker   # Taskiq worker with reload: runs the background jobs
vp run dev:scheduler # Taskiq scheduler: fires the hourly purge (run one)
vp run dev:web      # Next.js with Turbopack, http://localhost:3000
```

Each language is also available on its own:

```sh
vp install          # install Node dependencies
vp add / remove     # change Node dependencies
vp check [--fix]    # oxfmt + oxlint + tsc          (vp run check:ts)
vp test             # Vitest                         (vp run test:ts)
vp run -r build     # dependency-aware, cached task runner

uv sync --all-packages   # create .venv, install every Python project
uv add / remove          # change Python dependencies (run inside the project)
uv run ruff format .     # format                     (vp run check:py)
uv run ruff check .      # lint
uv run ty check          # type check
uv run pytest            # tests                      (vp run test:py)
```

A pre-commit hook (`.vite-hooks/`) runs `vp check --fix` on staged files and
`ruff check --fix` + `ruff format` on staged `*.py` files. Only the hook itself
is tracked; the shims and `core.hooksPath` are local to each clone, so run
`vp config` once after cloning to activate it.

## Adding projects

Drop projects into `apps/*`, `packages/*`, or `tools/*`; the workspace globs
already cover them. Each project extends a TypeScript preset from `tsconfig/`:

```text
tsconfig/
├── base.json      # shared strictness (never extended directly)
├── node.json      # Node apps, CLIs, workers
├── browser.json   # browser apps with DOM libs
└── library.json   # published packages with declarations + maps
```

```json
{
  "extends": "../../tsconfig/node.json",
  "compilerOptions": { "outDir": "./dist" },
  "include": ["src"]
}
```

Shared dev dependency versions come from the catalog in `pnpm-workspace.yaml`
(`"typescript": "catalog:"` etc.). Libraries build with `"build": "vp pack"`
(ESM, declarations, and source maps, configured once in the root
`vite.config.ts`). A project only adds its own `vite.config.ts` when it needs
runtime-specific behavior; a `build` script can also be anything else
(`wrangler deploy`, `tsc -p .`) and `vp run -r build` still orchestrates it.

### Python projects

Python projects go in the same folders, but uv rejects a workspace glob that
matches a directory without a `pyproject.toml`, so each one is listed in the
root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = ["apps/api", "packages/core-py"]
```

`uv init --app --package apps/<name>` (or `--lib packages/<name>`) scaffolds a
member with a `src/<package>/` layout and the `uv_build` backend. Put tests in
`tests/`. Ruff, ty, and pytest read their settings from the root
`pyproject.toml`, and the tools themselves are a root-level dependency group,
so a member declares only its own metadata and runtime dependencies.

## apps/api

A [FastAPI](https://fastapi.tiangolo.com) service, package `alloy_api`:

```text
apps/api/
├── pyproject.toml            # fastapi, pydantic-settings, sqlalchemy, psycopg, alembic, pwdlib, taskiq, taskiq-redis, redis; [tool.alembic]
├── compose.yaml              # local PostgreSQL 18, Redis 8, and RustFS (S3-compatible object storage)
├── Dockerfile                # the production image for the API, worker, and scheduler (see Deploying)
├── alembic.ini               # Alembic logging only
├── alembic/                  # env.py (async, URL from Settings), script.py.mako, versions/
├── .env.example
├── src/alloy_api/
│   ├── main.py               # app, lifespan (database engine), CORS, request IDs, router includes
│   ├── logs.py               # log format shared with the worker; the request_id context variable
│   ├── errors.py             # RequestIdMiddleware: X-Request-ID on every response, unhandled errors → plain 500
│   ├── config.py             # Settings (pydantic-settings) + get_settings dependency
│   ├── db.py                 # engine, session factory, get_session / SessionDep
│   ├── models.py             # declarative Base, naming convention, id/timestamp mixins; imports every model
│   ├── routers/health.py     # GET /health/ (liveness), GET /health/db and /health/redis (readiness)
│   ├── ratelimit.py          # fixed-window counters in Redis (or memory); the auth and invitation limits; per_ip / LimiterDep
│   ├── auth/                 # sign up, log in, log out; cookie sessions in Postgres; CurrentUserDep
│   ├── workspaces/           # workspaces, members, roles and permissions, invitations; CurrentMembership
│   ├── mail/                 # Mailer protocol + ConsoleMailer
│   ├── storage/              # ObjectStore protocol + S3ObjectStore (aiobotocore); ObjectStoreDep
│   ├── jobs/                 # Taskiq broker (Redis streams or in-memory), worker deps; tasks: emails, purge, imports
│   └── crm/                  # the Tiny CRM demo: companies, contacts, activities, tasks, attachments, imports, dashboard
└── tests/                    # TestClient fixture: settings overridden, one rolled-back transaction
```

```sh
vp run dev:api                # fastapi dev, reloads on change, http://127.0.0.1:8000/docs
cd apps/api && uv run fastapi run   # production server, no reload, 0.0.0.0
```

In production the same command runs inside the image from `apps/api/Dockerfile`;
see [Deploying](#deploying).

`[tool.fastapi] entrypoint` in `apps/api/pyproject.toml` tells the CLI where
the app is, so `fastapi dev` and `fastapi run` take no arguments (the CLI reads
it from the current directory, hence the `cd`). Settings come from environment
variables prefixed `ALLOY_` or a local `.env`; see `.env.example`. Tests override
`get_settings` through `app.dependency_overrides`, so the host environment never
leaks in.

FastAPI is pinned to a minor range (`>=0.141.1,<0.142`) because it is still
0.x and minor releases can break; Dependabot proposes the bump. Starlette is
not pinned, as the FastAPI docs advise. The `standard` extra without
`fastapi-cloud-cli` is used, since the template does not target FastAPI Cloud.
`httpx2` is a dev dependency because Starlette ≥ 1.6 prefers it for
`TestClient` and warns on `httpx`, which pytest treats as an error here.

Operation IDs are `{tag}-{function}` (`health-read_health`) via
`generate_unique_id_function`, the form the FastAPI docs recommend for
generated clients. `python -m alloy_api.openapi` prints the schema without
starting a server; `packages/api-client` uses it.

### Errors and request IDs

Every response carries an `X-Request-ID` header: the caller's, if it sent a
short printable one, otherwise 16 hex characters made for the request. The same
ID is on every log line written while handling the request (`logs.py` puts it
in a context variable and the log format), so a user's report finds its log
lines. An exception nothing handled becomes

```json
{ "detail": "Something went wrong. Quote the request ID when reporting it.", "request_id": "…" }
```

with status 500, one traceback in the log under that ID, and no internals in the
body. `RequestIdMiddleware` in `errors.py` does both; it sits inside CORS, so
the 500 still carries the CORS headers, and inside Logfire's span, so when a
token is set the ID reaches Logfire too. `apps/web` shows the ID after the
message on a 5xx and keeps it on `ApiError.requestId` for the others. Handled
errors (`HTTPException`) are unchanged: `{"detail": "..."}` with their status.

### Database

PostgreSQL 18 runs in Docker from `apps/api/compose.yaml`, with
[SQLAlchemy](https://docs.sqlalchemy.org) 2 in async mode over
[psycopg 3](https://www.psycopg.org/psycopg3/docs/) and
[Alembic](https://alembic.sqlalchemy.org) for migrations:

```sh
vp run db:up                  # start PostgreSQL, Redis, and RustFS, waits until healthy (127.0.0.1:5432, alloy/alloy)
vp run db:migrate             # alembic upgrade head
cd apps/api && uv run alembic revision --autogenerate -m "add widget"   # after changing models.py
cd apps/api && uv run alembic downgrade -1
vp run db:down                # stop; `docker compose down --volumes` in apps/api wipes the data
```

`psycopg[binary]` ships its own libpq, which the psycopg docs recommend for
most users; a production image that already has `libpq` can switch to
`psycopg[c]` to link against the system library instead. The URL scheme
`postgresql+psycopg` serves both sync and async engines, so scripts can use
the same driver without an event loop.

`ALLOY_DATABASE_URL` (default: the Compose database) is the one place the
connection is configured: the app reads it through `Settings`, and
`alembic/env.py` reads the same `Settings`, so `alembic.ini` holds no URL.
Alembic's own options live in `[tool.alembic]` in `pyproject.toml`. New
migration files are date-prefixed and run through Ruff by post-write hooks.

The engine is opened in the app lifespan and shared through `request.state`.
Handlers take a `SessionDep` and get one `AsyncSession` per request; commit
explicitly. `models.py` holds the `Base` (with a naming convention, so
constraints can be dropped by name in later migrations) plus the
`UUIDPrimaryKey` (UUIDv7, generated client-side) and `Timestamps` mixins, and
imports every feature's models at the bottom, because autogenerate only sees
what is on `Base.metadata`. Ruff is told that `Base` and `pydantic.BaseModel`
subclasses evaluate their annotations at runtime, and that the modules
exporting `*Dep` aliases are never moved into `TYPE_CHECKING` blocks, since
FastAPI reads dependency annotations at import time.

Tests use the real database, never SQLite. The `client` fixture opens one
connection, begins a transaction, runs `create_all` inside it, and hands out
sessions that join it with savepoints; the fixture rolls everything back, so
tests are isolated and the development database is left untouched (DDL is
transactional in PostgreSQL). `test_migrations_match_models` upgrades to head
inside such a transaction and diffs the result against `Base.metadata`, so a
model change without a migration fails CI. CI runs a `postgres:18` service
container with the same credentials.

### Authentication

`auth/` is a small, self-contained login system, kept apart from the demo so
it can stay when the CRM goes. Sessions are opaque and server-side: the
browser holds a random token in an `HttpOnly` cookie, PostgreSQL holds its
hash, and there are no JWTs to expire or rotate.

```text
POST /auth/signup      {email, password}                  → 201 UserRead + Set-Cookie
POST /auth/login       {email, password}                  → 200 UserRead + Set-Cookie   (401 on a bad email or password)
POST /auth/logout      cookie                             → 204, cookie cleared         (revokes this session)
POST /auth/logout-all  cookie                             → 204, cookie cleared         (revokes every session of the user)
POST /auth/password    cookie {current_password, new_password} → 204                    (revokes every other session)
GET  /auth/me          cookie                             → 200 UserRead

POST /auth/verify-email         {token}                   → 200 UserRead                (404 unknown/used, 410 expired)
POST /auth/resend-verification  cookie                    → 204                         (409 if already verified)
POST /auth/forgot-password      {email}                   → 204, always                 (emails a reset link if the account exists)
POST /auth/reset-password       {token, new_password}     → 200 UserRead + Set-Cookie   (404 unknown/used, 410 expired)
```

Logging in runs:

```text
verify password (Argon2id)
  → token = secrets.token_urlsafe(32)
  → INSERT user_sessions (token_hash = sha256(token), expires_at = now + ALLOY_SESSION_TTL)
  → Set-Cookie: __Host-session=<token>; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=...
```

and every authenticated request runs the reverse: cookie → hash → session
row (not revoked, not expired) → user → `Principal`. `CurrentUserDep` in
`auth/deps.py` is what a protected handler asks for; `CurrentPrincipal` also
gives the session, which logout needs. A missing, unknown, revoked, or
expired cookie is a 401. Logout sets `revoked_at` rather than deleting the
row, and `last_used_at` is refreshed at most every five minutes. Rows for
old sessions stay for `ALLOY_PURGE_AFTER` and are then removed by the purge
job (see Background jobs).

The cookie name's `__Host-` prefix makes browsers refuse it unless it is
`Secure`, has `Path=/`, and has no `Domain`, so it cannot be planted by a
sibling subdomain. Chrome and Firefox treat `http://localhost` as secure, so
`next dev` works as is; Safari does not, so use `next dev --experimental-https`
there. `SameSite=Lax` plus JSON-only bodies is the CSRF defence: a cross-site
form post neither carries the cookie nor passes body validation, and no `GET`
changes state. CORS is configured with `allow_credentials=True` and the
explicit `ALLOY_CORS_ORIGINS` list a credentialed request requires.

The Next.js side needs no auth library. Whether it calls the API from the
browser (`credentials: "include"`) or from a Route Handler that forwards the
`Cookie` and `Set-Cookie` headers, the cookie is the whole session, and the
API stays the authority on who is logged in.

Passwords are hashed with Argon2id through [pwdlib](https://frankie567.github.io/pwdlib/),
which the FastAPI security tutorial recommends, in a worker thread so hashing
never blocks the event loop. An unknown email is verified against a dummy
hash so both failures take about as long. Emails are stored lower-cased and
must be unique (409 on signup). The `APIKeyCookie` scheme is in the OpenAPI
schema, so the generated client knows which endpoints are protected.

Two flows run through an emailed link, and both work the same way as a
session token: the email carries `secrets.token_urlsafe(32)`, the `users` row
holds its SHA-256 plus a `*_sent_at` timestamp, and the link is spent by
clearing both. Signup emails a verification link (`ALLOY_VERIFICATION_TTL`,
default 1 day); until it is followed, everything past `/auth/*` answers 403.
`/auth/forgot-password` emails a reset link (`ALLOY_PASSWORD_RESET_TTL`,
default 1 hour) and answers 204 whether or not the address has an account, so
it does not reveal who is registered. `/auth/reset-password` sets the
password, revokes every session, and logs the browser in with a fresh one;
following the link proves the address, so it also counts as verification. A
new request replaces the pending link, and changing the password while logged
in voids it. Links point at `ALLOY_FRONTEND_URL/verify-email?token=` and
`/reset-password?token=`; the pages confirm with a click, so a mail scanner
that prefetches the link does not spend it.

### Rate limits

`ratelimit.py` guards what can be called without a login, plus the two
logged-in endpoints that send mail or take a token. Fixed-window counters:
the first hit starts a window, each hit adds one, and past the limit the
answer is 429 with `Retry-After` set to what is left of the window. A
`Limit` names the policy; the subject (client address, email, user id) picks
the counter. Routes attach `per_ip(limit)` as a dependency, or call the
`Limiter` themselves when the subject is in the body or only failures should
count.

| Endpoint                                                             | Subject         | Limit         |
| -------------------------------------------------------------------- | --------------- | ------------- |
| `POST /auth/login`                                                   | address         | 20 per 15 min |
| `POST /auth/login`                                                   | email, failures | 10 per 15 min |
| `POST /auth/signup`                                                  | address         | 10 per hour   |
| `POST /auth/forgot-password`                                         | address         | 10 per hour   |
| `POST /auth/forgot-password`                                         | email           | 3 per hour    |
| `POST /auth/resend-verification`                                     | user            | 3 per hour    |
| `POST /auth/verify-email`, `/reset-password`, `GET /invites/{token}` | address         | 10 per minute |
| `POST /invites/{token}/accept`                                       | user            | 10 per minute |

Login checks both counters before the password hash, which is slow by design,
so a blocked attempt costs nothing; the email counter counts wrong passwords
only and is cleared by a right one, so a botnet working on one account is
stopped without locking the real user out for good. `forgot-password` counts
per address whether or not the account exists, so the limit reveals nothing
the 204 hides. Every trip is logged at WARNING with the limit's name and the
subject.

The counters live in Redis (`ALLOY_RATE_LIMIT_STORE=redis`, the default, on
`ALLOY_REDIS_URL`), so every API instance shares them; `memory` keeps them in
the process for development without Redis, and the tests use a fresh
in-memory store per test. The address is `request.client`, which Uvicorn
fills from `X-Forwarded-For` when the peer is in `FORWARDED_ALLOW_IPS`: the
web app's proxy route sets that header to the visitor's address, and the API
image trusts every peer because only that route can reach it (see Deploying).
Unset the trust and every request counts against the proxy's one address.

### Workspaces, roles, and invitations

Every business record belongs to a workspace, and a user reaches it through a
seat in that workspace (`workspace_members`) with one of four roles. Signing
up creates a first workspace with the new user as owner.

```text
GET/POST          /workspaces/                              the caller's workspaces (with role and permissions) / create one as owner
GET/PATCH/DELETE  /workspaces/{id}                          read · rename (workspace:manage) · delete with everything in it (workspace:delete)
POST              /workspaces/{id}/leave                    give up your seat; the last owner cannot
GET               /workspaces/{id}/members                  members:read
PATCH/DELETE      /workspaces/{id}/members/{member_id}      change role · remove (members:manage)
GET/POST          /workspaces/{id}/invites                  pending invitations · email a link {email, role} (members:manage)
DELETE            /workspaces/{id}/invites/{invite_id}      revoke
GET               /invites/{token}                          preview, no login (404 unknown/used/revoked, 410 expired)
POST              /invites/{token}/accept                   take the seat; the account's email must match
```

| Role   | Permissions                                                                   |
| ------ | ----------------------------------------------------------------------------- |
| owner  | everything, including `workspace:delete`                                      |
| admin  | `crm:read`, `crm:write`, `members:read`, `members:manage`, `workspace:manage` |
| member | `crm:read`, `crm:write`, `members:read`                                       |
| viewer | `crm:read`, `members:read`                                                    |

`workspaces/permissions.py` is the one place roles map to permissions.
Handlers never ask for a role: they take one of the `Can*` dependencies from
`workspaces/deps.py` (`CanReadCrm`, `CanWriteCrm`, `CanManageMembers`, ...),
each of which loads the caller's membership of `{workspace_id}` (404 for
non-members, so ids leak nothing) and returns 403 when the role lacks the
permission. Managing seats follows one rule, `can_manage_role`: owners manage
everyone, others only roles below their own, and a workspace always keeps at
least one owner (409 otherwise).

Invitations are emailed links. The token is random, only its SHA-256 is
stored, and the row is stamped `accepted_at` or `revoked_at` rather than
deleted. A link works for `ALLOY_INVITE_TTL` (default 7 days) and only for the
invited address, which the accepting account's email must match. The link
points at `ALLOY_FRONTEND_URL/invites/{token}`.

### Email

`mail/` keeps the app one step away from any email provider. `Mailer`
(`mail/base.py`) is a protocol with a single `send(Email)` method;
`ConsoleMailer` implements it by logging the message at INFO, which is what
`fastapi dev` and the tests use. `create_mailer(settings)` picks the
implementation from `ALLOY_MAIL_PROVIDER`. Handlers never call it: they build
the `Email` and queue it with `send_email.kiq(email)` (see Background jobs),
so a slow or failing provider never delays a response, and the worker is the
only process that holds the mailer. To add Resend or another provider: write
a class with the same `send` method, add its name to `MailProvider`, return it
from `create_mailer`, and read its credentials from `Settings`. Nothing else
changes. Tests give the in-memory broker an outbox as its mailer and read the
invitation token out of the message body.

### Object storage

`storage/` keeps the app one step away from any storage service, the way
`mail/` does for email. `ObjectStore` (`storage/base.py`) is a protocol with
`put`, `get`, `head`, `delete`, `delete_prefix`, `upload_url`, and
`download_url`. `S3ObjectStore` (`storage/s3.py`) implements it over
[aiobotocore](https://github.com/aio-libs/aiobotocore) and is the only
implementation, because every candidate speaks S3: [RustFS](https://rustfs.com)
locally (Apache 2.0, from `compose.yaml`), and AWS S3, Cloudflare R2, Garage,
or SeaweedFS when hosted. Switching is configuration:

```sh
ALLOY_STORAGE_ENDPOINT_URL=null          # AWS itself; a URL for anything S3-compatible
ALLOY_STORAGE_PUBLIC_ENDPOINT_URL=...    # only when the browser reaches storage at another address than the API does
ALLOY_STORAGE_PATH_STYLE=false           # AWS; true (default) for RustFS and MinIO
ALLOY_STORAGE_REGION / _BUCKET / _ACCESS_KEY / _SECRET_KEY
```

`create_object_store(settings)` builds the store, the lifespan enters it,
and handlers take an `ObjectStoreDep`. To add a backend that does not speak
S3: write a class with the same methods, add its name to `StorageProvider`,
return it from `create_object_store`. `tests/test_storage.py` is the contract:
the same tests run against `MemoryObjectStore` (`storage/memory.py`, the
test double the route tests use) and against the RustFS from Compose, plus
presigned-URL tests that need the real server.

Bytes never pass through the API. The browser uploads with a presigned `PUT`
and downloads through a presigned `GET`, both signed by the store for
`ALLOY_STORAGE_URL_TTL` (default 15 minutes). A presigned `PUT` pins the
`Content-Type` and the `Content-Length` the client declared, so storage refuses
a body of another type or size before writing it, and the object key never
comes from the client. Keys are `workspaces/{id}/attachments/{id}`, so
deleting a workspace clears its files with one `delete_prefix`. The `storage-init`
Compose service creates the bucket and sets its CORS rule for
`http://localhost:3000`; a hosted bucket needs the same rule for the web
app's origin. The RustFS console is at http://localhost:9001 (`rustfsadmin` /
`rustfsadmin`).

### Background jobs

`jobs/` runs work outside the request on [Taskiq](https://taskiq-python.github.io)
with [taskiq-redis](https://github.com/taskiq-python/taskiq-redis). There
are three tasks, one per module:

| Task            | Module            | Trigger                                                   | What it does                                                                                                        |
| --------------- | ----------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `mail.send`     | `jobs/emails.py`  | signup, resend verification, forgot password, invitations | Hands the `Email` to the mailer; retried up to 5 times with backoff                                                 |
| `purge.expired` | `jobs/purge.py`   | hourly (`schedule` label), or by hand                     | Deletes revoked/expired sessions, used/expired invitations, expired verification and reset links, abandoned uploads |
| `imports.run`   | `jobs/imports.py` | `POST .../imports/{id}/start`                             | Loads a CSV of contacts or companies (`crm/importing.py`); records counts and per-row errors                        |

```sh
vp run dev:worker             # taskiq worker alloy_api.jobs.broker:broker --reload
vp run dev:scheduler          # taskiq scheduler alloy_api.jobs.broker:scheduler --skip-first-run
cd apps/api && uv run taskiq worker alloy_api.jobs.broker:broker --workers 4   # production
```

`ALLOY_JOBS_BROKER` picks the broker in `create_broker(settings)`:

- `redis` (default): `RedisStreamBroker` on `ALLOY_REDIS_URL`. Streams, not
  lists or pub/sub, because they have acknowledgements: a message is removed
  only when a worker has finished it, so a crashed worker's message is
  redelivered. Results go to a `RedisAsyncResultBackend` with a one-hour
  expiry. `SmartRetryMiddleware` retries tasks labelled `retry_on_error`
  with exponential backoff and jitter; the stream broker cannot delay a
  message itself, so a retry is put on a `ListRedisScheduleSource` and the
  scheduler sends it when due.
- `memory`: Taskiq's `InMemoryBroker`. The API process runs each task in the
  background with its own engine, mailer, and store; no Redis, no worker, no
  scheduler. Good for a laptop without Docker, and what the tests use.

The worker and the scheduler are separate processes that import the same
`jobs/broker.py`. The worker opens a database engine, a mailer, and an object
store per process at `WORKER_STARTUP` and puts them on `TaskiqState`; tasks
declare what they need as defaults (`session: AsyncSession =
TaskiqDepends(get_session)`, from `jobs/deps.py`), never a request. The
scheduler reads the `schedule` labels (`purge.expired` is
`{"cron": "0 * * * *"}`) and the delayed retries; run exactly one, as the
Taskiq docs say, or periodic tasks fire twice. `--skip-first-run` stops it
from firing every cron task the moment it starts. `GET /health/redis` pings
the Redis behind the queue for readiness probes.

Tasks are ordinary async functions and stay callable as such. In tests the
broker is in-memory with `await_inplace`, so `kiq()` runs the task before it
returns, on the test transaction and with the same doubles the handlers get:
a handler that queues an email has the message in `outbox` when it responds.
`tests/test_jobs.py` also checks the Redis wiring against the Compose Redis.

The purge job removes rows the app stamps rather than deletes, once they have
been dead for `ALLOY_PURGE_AFTER` (default 7 days): sessions revoked or
expired, invitations accepted, revoked, or expired, verification and password
reset links past their TTL, and attachment or import rows whose upload URL expired without a
completion, along with any object that did land in storage.

### CSV imports

`POST .../imports` starts an import of contacts or companies the way an
attachment upload does: the API returns an upload URL for the CSV
(`text/csv`, at most `ALLOY_IMPORT_MAX_BYTES`, default 10 MB), the browser
`PUT`s the file there, and `POST .../imports/{id}/start` confirms it is in the
store and queues `imports.run`. `GET .../imports/{id}` shows the row move
through `pending → queued → running → done | failed`, with counts of rows
created, skipped, and failed, the first 100 row errors as `{row, message}`
(`row` is the line in the file), and `error` when the file could not be read
at all. The CSV is removed from storage when the job ends.

```text
GET/POST          .../imports/                   newest first / start an import {kind, filename, size} → upload URL
GET               .../imports/{id}               progress and outcome
POST              .../imports/{id}/start         after the PUT; 409 until the file is in the store or if already started
```

The file is UTF-8 (a BOM is fine) with a header row; headers match
case-insensitively with spaces as underscores, and unknown columns are
ignored. Contacts take `name, email, phone, job_title, status, company`;
companies take `name, website, industry, notes`. Each row is validated as a
`POST` body would be, so the rules match the forms. A contact whose email is
already in the workspace and a company whose name is (case-insensitively) are
skipped, not duplicated; a contact's `company` links an existing company or
creates it once for the file. The rows are written in one transaction with
the final status, so a run that dies halfway leaves nothing behind and is
simply run again when the broker redelivers it.

The web app's Imports page (`apps/web/src/app/(app)/[workspaceId]/imports/`)
drives this handshake: pick the kind and a file, watch the upload, then the
history table polls every two seconds while a job is queued or running and
opens the row errors in a dialog once it is done.

### Tiny CRM (demo)

`crm/` is a sample application on top of the template: contacts, companies,
an activity feed per contact, tasks, and a dashboard, for freelancers and
small teams. It exists to show the setup end to end and can be deleted as a
unit (the package, its migration, its tests, and two lines in `main.py`).

Every row belongs to a workspace (`OwnedByWorkspace` mixin), every query
filters on the workspace in the URL, and a row from another workspace is a
404, whether it is addressed in the path or referenced from a body
(`company_id`, `contact_id`). Reads need `crm:read`, writes `crm:write`
(403 for viewers). Lists take `limit` (≤ 500) and `offset` and answer with a
page, `{items, total, limit, offset}`, where `total` counts every row the
filters match, so a client can page through all of them. The contact, company,
and task lists also take `sort` (a column of the table) and `order`
(`asc` / `desc`); a row without a value for the sort column comes last either
way, and ties keep creation order so pages never overlap. `PATCH` bodies are
partial: a field left out is untouched, a field sent as `null` is cleared.

```text
                  /workspaces/{workspace_id}/...  every route below hangs off a workspace

GET/POST          .../companies/                 ?q= &sort=name|industry|created_at &order=
GET/PATCH/DELETE  .../companies/{id}                            delete keeps contacts and tasks, clears the link
GET               .../companies/{id}/contacts

GET/POST          .../contacts/                  ?q= &status= &company_id= &sort=name|company|status|last_contacted_at &order=
GET/PATCH/DELETE  .../contacts/{id}                             delete removes the activity feed, keeps tasks
GET/POST          .../contacts/{id}/activities                  newest first

GET/POST          .../tasks/                     ?due=overdue|today|upcoming &tz= &status= &contact_id= &company_id= &sort=due_at|title|contact|company &order=
GET/PATCH/DELETE  .../tasks/{id}

GET               .../dashboard/                 ?tz= &stale_days=30 &limit=5
GET/POST          .../contacts/{id}/attachments                  uploaded files, newest first / start an upload
GET/POST          .../companies/{id}/attachments
POST              .../attachments/{id}/complete                 after the PUT; 409 until the object is in the store
GET               .../attachments/{id}/download                 307 to a short-lived storage URL
DELETE            .../attachments/{id}                          removes the object, then the row
GET/POST          .../imports/                                  CSV imports of contacts or companies (see above)
```

- Contact `status`: `lead`, `active`, `inactive`. Task `status`: `open`,
  `done`. Activity `type`: `note`, `call`, `email`, `meeting`, `follow_up`,
  `task_completed`. Enums are stored as `VARCHAR`, so adding a member needs
  no migration.
- Logging a call, email, meeting, or follow-up sets the contact's
  `last_contacted_at`; a note does not. Marking a task `done` logs a
  `task_completed` activity on its contact (once).
- "Today" depends on where the user is, so `tz` takes an IANA zone (default
  `UTC`). Overdue means due before today, upcoming means due after it, and
  undated tasks are neither. `due` and `status` filter independently; the
  dashboard counts only open tasks.
- The dashboard lists the most recently contacted people and those not
  contacted in `stale_days` (never-contacted last).
- Attachments are files on a contact or a company, at most
  `ALLOY_ATTACHMENT_MAX_BYTES` (default 25 MB). An upload is a handshake: `POST`
  the filename, type, and size to get an upload URL (413 when too big), `PUT`
  the file there, `POST .../complete` so the API confirms the object is in the
  store, records the size storage actually received, and marks the row
  uploaded. Rows whose upload never completed stay hidden. Deleting a contact,
  company, or workspace deletes its files from storage first.

## packages/api-client

A typed fetch client for `apps/api`, package `@alloy/api-client`, built on
[openapi-fetch](https://openapi-ts.dev/openapi-fetch/) with types generated by
[openapi-typescript](https://openapi-ts.dev):

```text
packages/api-client/
├── package.json              # openapi-fetch; openapi-typescript + typescript 5 (dev)
├── vite.config.ts            # generate / generate:check tasks, uncached
├── scripts/generate.ts       # export schema from apps/api, generate types, or --check
├── openapi.json              # committed: the exported schema
└── src/
    ├── generated/schema.ts   # committed: paths, components, operations types
    ├── index.ts              # createApiClient() + re-exported types
    └── index.test.ts
```

```ts
import { createApiClient } from "@alloy/api-client";

const api = createApiClient({ baseUrl: "http://127.0.0.1:8000" });
const { data, error } = await api.GET("/health/"); // data: { status: string }
```

```sh
vp run generate           # regenerate after changing a route or model in apps/api
vp run check:generated    # fail if openapi.json or schema.ts is stale; CI runs this
```

Both generated files are committed so consumers never need Python installed
and schema changes show up in review.

`exports` points at `src/index.ts`, so `apps/web` (whose bundler compiles
workspace packages) consumes the source and `next dev` needs no build step;
`publishConfig.exports` swaps in `dist/` if the package is ever published, and
`vp pack` still builds it.

`scripts/generate.ts` runs under Node's native type stripping, calls `uv run --package alloy-api python -m
alloy_api.openapi`, and feeds the result to the openapi-typescript Node API
with `rootTypes` on, so every component schema is also a top-level alias
(`Health`, not only `components["schemas"]["Health"]`).

openapi-typescript builds its output with the TypeScript JS compiler API, which
the TypeScript 7 package (the Go port) no longer ships. The package therefore
declares its own `typescript: ^5.9` dev dependency instead of the catalog, and
pnpm resolves openapi-typescript's peer from it; the rest of the workspace,
including `vp check` and `vp pack`, stays on TypeScript 7.

## apps/web

A [Next.js](https://nextjs.org/docs) 16 app (App Router, Turbopack, TypeScript),
package `@alloy/web`: the front end for the Tiny CRM, with login, a dashboard,
contacts, companies, tasks, and CSV imports.

```text
apps/web/
├── package.json              # next, react; @alloy/api-client; zod; @tanstack/react-{query,form,table}; tailwindcss; @base-ui/react, lucide-react, sonner
├── next.config.ts            # cacheComponents, typedRoutes, reactCompiler, skipTrailingSlashRedirect, standalone output
├── Dockerfile                # the production image (see Deploying)
├── postcss.config.mjs        # @tailwindcss/postcss
├── components.json           # shadcn/ui config: base-nova style, zinc, src/app/globals.css
├── tsconfig.json             # tsconfig/browser.json + jsx, paths (@/*), next plugin
├── .env.example              # API_URL
└── src/
    ├── proxy.ts              # redirects on the session cookie's presence (formerly middleware)
    ├── app/
    │   ├── layout.tsx, providers.tsx   # font, QueryClientProvider, next-themes, toasts
    │   ├── api/[...path]/route.ts      # forwards /api/* to the FastAPI service with the cookie
    │   ├── (auth)/login, signup        # one shared client form
    │   └── (app)/                      # sidebar layout with nav + user menu; dashboard, contacts, companies, tasks, imports, settings
    ├── components/
    │   ├── ui/               # shadcn/ui components, added with `pnpm dlx shadcn@latest add`
    │   ├── form/             # TanStack Form hook bound to shadcn Field components
    │   └── data-table.tsx    # TanStack Table v9 with sorting and paging
    └── lib/
        ├── api.ts, session.ts, api-browser.ts   # the typed client, server-side and browser-side
        ├── queries.ts        # TanStack Query definitions shared by both sides
        ├── schemas.ts        # Zod schemas for every form and URL
        └── dates.ts, time-zone.ts               # the user's zone, for "today"
```

```sh
vp run dev:web                # next dev, http://localhost:3000
cd apps/web && vp run build   # next build (part of vp run -r build)
cd apps/web && vp run start   # production server
cd apps/web && vp run typegen # regenerate next-env.d.ts and .next/types without a build
```

The browser only talks to Next.js. `API_URL` is read on the server (no
`NEXT_PUBLIC_` prefix), and `src/app/api/[...path]/route.ts` forwards `/api/*`
to it with the session cookie, so one build can target a different API per
environment and no CORS setup is needed. See `apps/web/README.md` for how the
pages split between Server and Client Components, how data flows through
TanStack Query, and how forms and tables are built.

Choices worth knowing, all from the Next.js 16 docs:

- `cacheComponents: true`: the current caching model. Routes prerender a static
  shell; uncached reads go behind `<Suspense>` and stream, or opt in with
  `"use cache"`. `next build` reports every route as Partial Prerender.
- `typedRoutes: true`: `<Link href>` and `router.push()` are checked against the
  routes generated in `.next/types`.
- `reactCompiler: true`: the React Compiler memoizes components and values
  automatically, so write plain React and reach for `useMemo`/`useCallback`
  only for precise control, as the React docs advise. It runs as
  `babel-plugin-react-compiler` on files with JSX or hooks only. The
  Babel-free `experimental.turbopackRustReactCompiler` exists but is not yet
  recommended for production.
- `skipTrailingSlashRedirect: true`: the FastAPI collection routes end in a
  slash (`/contacts/`), and Next.js would otherwise 308 `/api/contacts/` to
  `/api/contacts` before the proxy route could forward it.
- Tailwind CSS v4 through `@tailwindcss/postcss`, configured in CSS only, and
  shadcn/ui (`base-nova` style on Base UI primitives) initialized from a preset.
  See `apps/web/README.md` for the theme layout and how to add components.
- No ESLint. Next 16 no longer lints during `next build`; oxlint via `vp check`
  covers the app like every other package.
- TypeScript 7 from the catalog: `next build` runs the project-local `tsc` CLI
  by default, which is what makes TS 7 work.
- `next-env.d.ts`, `.next/`, and `out/` are gitignored. `tsconfig.json` includes
  the generated types when present, and `vp check` passes on a fresh clone
  without them.
- The `vp run` task cache never hits for `@alloy/web#build` because `next build`
  writes into the project directory; the API client and other packages still
  cache.

## Deploying

The template does not pick a host. It ships what every host needs: an image
per app, one command per process, settings from environment variables, and a
migration step to run before new code starts.

```text
apps/api/Dockerfile           # API, worker, and scheduler: one image, three commands
apps/web/Dockerfile           # Next.js standalone output
.dockerignore                 # both build from the repository root (uv and pnpm workspaces)
.github/workflows/images.yml  # builds and pushes ghcr.io/<owner>/<repo>/{api,web} after CI passes on main
```

### Processes

| Process     | Image      | Command                                                  | Port | Instances |
| ----------- | ---------- | -------------------------------------------------------- | ---- | --------- |
| `api`       | `apps/api` | `fastapi run --port 8000 --proxy-headers` (the default)  | 8000 | any       |
| `worker`    | `apps/api` | `taskiq worker alloy_api.jobs.broker:broker --workers 2` | none | any       |
| `scheduler` | `apps/api` | `taskiq scheduler alloy_api.jobs.broker:scheduler`       | none | exactly 1 |
| `web`       | `apps/web` | `node apps/web/server.js` (the default)                  | 3000 | any       |

Plus PostgreSQL 18, Redis, and an S3-compatible bucket, which every host
offers managed. Only `web` needs a public address: the browser talks to
Next.js, and its proxy route forwards `/api/*` to the API over the host's
private network, so the API stays internal and needs no CORS. The bucket must
be reachable by the browser, since uploads and downloads use presigned URLs.

The proxy route passes the visitor's address upstream as `X-Forwarded-For`,
read from the platform's own header (`CF-Connecting-IP`, `X-Real-IP`, or the
last entry of `X-Forwarded-For`), and the API image sets
`FORWARDED_ALLOW_IPS=*` so Uvicorn believes it from any peer. That is safe
while the API is reachable only from `web`; if it ever gets a public address,
set `FORWARDED_ALLOW_IPS` to the web service's address or network instead.

### Migrations

Run `alembic upgrade head` from `/app/apps/api` in the API image before the
new `api`, `worker`, and `scheduler` start. Every host has a hook for this:
Railway's pre-deploy command, Render's pre-deploy command, Fly's
`release_command`, a Kubernetes init container or Job. If it fails, the deploy
stops and the old code keeps running. Migrations are written to be safe to
apply before the old code stops (add, backfill, drop in a later release), which
is what makes this ordering enough.

### Settings and secrets

Every process reads the same `ALLOY_*` variables, documented in
`apps/api/.env.example`; `web` reads `API_URL`. Set them in the host's
variables store, shared across the four processes. Nothing is baked into an
image, so one image serves staging and production. The ones that change per
environment:

```sh
ALLOY_DATABASE_URL=postgresql+psycopg://...      # from the managed PostgreSQL
ALLOY_REDIS_URL=redis://...                      # from the managed Redis
ALLOY_STORAGE_ENDPOINT_URL=...                   # the bucket's S3 endpoint; null for AWS S3
ALLOY_STORAGE_PUBLIC_ENDPOINT_URL=...            # only if the browser reaches the bucket at a different address
ALLOY_STORAGE_ACCESS_KEY=... ALLOY_STORAGE_SECRET_KEY=... ALLOY_STORAGE_BUCKET=...
ALLOY_STORAGE_PATH_STYLE=false                   # AWS and most hosted S3; true for MinIO and RustFS
ALLOY_FRONTEND_URL=https://app.example.com       # links in emails
ALLOY_CORS_ORIGINS='["https://app.example.com"]'
ALLOY_LOGFIRE_TOKEN=...                          # optional; empty turns telemetry off
ALLOY_LOGFIRE_ENVIRONMENT=production
API_URL=http://api.internal:8000                 # web only: the API's private address
```

Unset optionals may arrive as `""` from a variables UI; `Settings` ignores
empty values, so that reads as the default.

### Example: Railway

Four services from one repository, each with its Dockerfile path set in the
service settings (`apps/api/Dockerfile` for `api`, `worker`, and `scheduler`,
with the commands above as start commands; `apps/web/Dockerfile` for `web`),
plus the PostgreSQL and Redis plugins and an external bucket (S3, R2, or any
S3-compatible service). Set `alembic upgrade head` as the pre-deploy command
on `api`. Give `web` the public domain; `API_URL` is
`http://api.railway.internal:8000` on the private network. Railway builds from
the repository, so the Images workflow is not needed; it serves hosts that
pull from a registry instead.

### Choices worth knowing

- **One image for the API, worker, and scheduler.** They share code and
  settings; only the command differs. uv installs from the lockfile in a build
  stage, and the runtime stage is the plain `python:3.14-slim` image with the
  virtualenv copied in, as a non-root user.
- **Next.js standalone output.** `output: "standalone"` in `next.config.ts`
  traces the files the server needs, so the runtime image holds no
  `devDependencies` and no source. `API_URL` is read at runtime, so the build
  takes no configuration.
- **Images from CI, when a host wants them.** The Images workflow runs on
  `workflow_run` after CI, so a red commit never gets an image, and tags
  `latest` plus `sha-<short sha>` so a deploy can pin or roll back to an exact
  build.
- **Email is still the console mailer.** Invitation, verification, and password
  reset links are printed in the worker's logs until a real provider is added; see
  [Email](#email).
- **No Compose file, no host config.** Both would tie the template to one
  layout. The table above is the whole wiring; each host has a place for it.

## Supply-chain policy

Defined in `pnpm-workspace.yaml`:

- `minimumReleaseAge: 5760`: new versions must be ≥ 4 days old before resolving
- `strictDepBuilds` + `allowBuilds: {}`: no dependency runs lifecycle scripts
  until explicitly reviewed and listed
- `blockExoticSubdeps`: transitive deps must come from the registry
- `trustPolicy: no-downgrade`: publisher trust levels may not regress.
  `trustPolicyExclude` lists the exact versions that are known false positives
  (currently `semver@6.3.1`, an old major that `@babel/core` still needs,
  published without provenance days after a 7.x release that had it)
- `verifyDepsBeforeRun`: scripts never run against a stale tree
- `engineStrict`: Node version mismatch fails instead of warning

And in `pyproject.toml`:

- `exclude-newer = "4 days"`: new releases must be ≥ 4 days old before
  resolving, recorded in `uv.lock` as a duration so the lockfile stays
  reproducible
- `required-version`: uv version mismatch fails instead of misbehaving

CI (`.github/workflows/ci.yml`) uses least-privilege permissions, SHA-pinned
actions, and frozen lockfiles. `setup-vp` installs Vite+, Node, and pnpm and
caches the store; `setup-uv` does the same for Python. The `vp run` task cache
is restored and saved around the build. Dependabot runs weekly on npm, uv, and
GitHub Actions with a 4-day cooldown matching both policies.

## License

[MIT](LICENSE) © builtbystef
