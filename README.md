# Alloy

An opinionated template for web apps: TypeScript + Next.js in front, Python +
FastAPI behind. Extends [carbon-fiber](https://github.com/builtbystef/carbon-fiber).
Each language has one toolchain for dependencies, formatting, linting, type
checking, and tests:

| Concern    | TypeScript                                    | Python                          |
| ---------- | --------------------------------------------- | ------------------------------- |
| Packages   | pnpm via [Vite+](https://viteplus.dev) (`vp`) | [uv](https://docs.astral.sh/uv) |
| Format     | oxfmt (`vp check`)                            | Ruff (`ruff format`)            |
| Lint       | oxlint (`vp check`)                           | Ruff (`ruff check`)             |
| Type check | tsc (`vp check`)                              | [ty](https://docs.astral.sh/ty) |
| Tests      | Vitest (`vp test`)                            | pytest                          |
| Config     | `vite.config.ts`, `tsconfig/`                 | `pyproject.toml`                |

## Requirements

- Node ≥ 24 (`.node-version`), Python ≥ 3.14 (`.python-version`, uv downloads it), uv ≥ 0.12
- Docker with Compose, for the local PostgreSQL and RustFS that `apps/server` and its tests use

## Commands

```sh
vp run check         # format + lint + typecheck, both languages (check:fix to apply fixes)
vp run test          # Vitest + pytest
vp run build
vp run ci            # everything CI runs
vp run db:up         # PostgreSQL and RustFS in Docker; waits until ready
vp run db:migrate    # alembic upgrade head
vp run db:down       # stop (data is kept; add --volumes to wipe it)
vp run dev           # API, worker, and web together, one colour-coded console
vp run dev:api       # FastAPI with reload, http://127.0.0.1:8000/docs
vp run dev:worker    # the background jobs and the hourly purge, restarted on changes
vp run dev:web       # Next.js, http://localhost:3000
```

Per language: `vp install / add / remove / check [--fix] / test` and
`uv sync --all-packages / add / remove / run ruff / run ty check / run pytest`.
A pre-commit hook in `.vite-hooks/` runs `vp check --fix` and Ruff on staged
files; run `vp config` once after cloning to activate it.

## Adding projects

Projects go in `apps/*`, `packages/*`, or `tools/*`. A TypeScript project
extends a preset from `tsconfig/` (`node.json`, `browser.json`, or
`library.json`), takes shared versions from the catalog in
`pnpm-workspace.yaml` (`"typescript": "catalog:"`), and builds with `vp pack`
unless it needs something else. A Python project is scaffolded with
`uv init --app --package apps/<name>` (or `--lib packages/<name>`) and listed
under `[tool.uv.workspace] members` in the root `pyproject.toml`, which also
holds the Ruff, ty, and pytest settings.

## apps/server

The backend: a [FastAPI](https://fastapi.tiangolo.com) app, a Procrastinate worker, and the assistant agent. Package `alloy_server`:

```text
apps/server/
├── compose.yaml              # local PostgreSQL 18 (also the job queue), RustFS (S3-compatible storage)
├── Dockerfile                # one image for the API and the worker
├── alembic/                  # env.py reads the URL from Settings; versions/
├── .env.example              # every ALLOY_* setting, documented
├── src/alloy_server/
│   ├── main.py               # app, lifespan (engine, store, job queue), middleware, the AppError handler
│   ├── config.py             # Settings (pydantic-settings) + get_settings
│   ├── shared/               # exceptions.py (AppError family + handler), middleware.py (request IDs, body limit), logs.py, telemetry.py, routing.py
│   ├── db/                   # session.py (engine, SessionDep), base.py (Base, mixins), models.py (imports every model)
│   ├── integrations/         # ports and adapters: mail/, storage/, ratelimit/, ai/ (a protocol + implementations each)
│   ├── modules/              # the features, one package each; router.py includes every feature router
│   │   ├── health/           # GET /health/ (liveness); /health/{db,storage} (readiness)
│   │   ├── auth/             # accounts, cookie sessions, emailed links; CurrentUserDep
│   │   ├── workspaces/       # workspaces, members, roles, invitations; the Can* dependencies
│   │   ├── crm/              # the demo: companies/, contacts/, tasks/, attachments/, imports/, dashboard/ + shared mixins, pagination, ownership
│   │   └── assistant/        # the assistant: a Pydantic AI agent (agent.py) over the CRM
│   └── jobs/                 # Procrastinate app, task decorator, worker; tasks: emails, purge, imports, stalled
└── tests/
    ├── unit/                 # no PostgreSQL, no object storage: `uv run pytest apps/server/tests/unit` runs anywhere
    └── integration/          # the app over a real database; one rolled-back transaction per test
```

A modular monolith without machinery. Each module under `modules/` has only
the files it needs: `router.py` (paths, status codes, dependencies, `commit`),
`schemas.py` (Pydantic), `models.py` (SQLAlchemy), `service.py` (the work:
takes a session and parsed input, owns the queries, raises `AppError`s rather
than `HTTPException`s), and `dependencies.py` for dependencies other modules
use. There is no repository layer: the session is the unit of work. The
assistant's tools and the worker's jobs call the same service functions the
routes do.

Two rules keep the modules apart. A module imports `config`, `db`, `shared`,
`integrations`, and other modules only through their `service`, `models`, and
`dependencies`. Nothing outside `modules/` imports a module except
`db/models.py`, the list that registers every model, and the jobs that run for
them; `modules/router.py` is the HTTP composition root that includes every
feature router.

Settings come from `ALLOY_*` environment variables or a local `.env`; tests
override `get_settings`. Operation IDs are `{tag}-{function}`, and
`python -m alloy_server.openapi` prints the schema for `packages/api-client`.
The routes are documented at `/docs`; the sections below cover behaviour that
is not obvious from them.

### Errors, logs, and request IDs

Every response carries `X-Request-ID` (the caller's, or one made for the
request), and the same ID is on every log line the request writes, including
in the worker for jobs it queues. Logs are one shape everywhere;
`ALLOY_LOG_FORMAT=json` makes them one object per line. An unhandled
exception becomes a plain 500 with the request ID and no internals. Services
raise `AppError` subclasses (`NotFoundError`, `ConflictError`,
`RateLimitedError`, ...) and `handle_app_error` gives them the same
`{"detail": ...}` body an `HTTPException` gets.

### Database

SQLAlchemy 2 async over psycopg 3, migrations with Alembic:

```sh
cd apps/server && uv run alembic revision --autogenerate -m "add widget"
cd apps/server && uv run alembic downgrade -1
```

`ALLOY_DATABASE_URL` is the one place the connection is configured; Alembic
reads the same `Settings`. Handlers take a `SessionDep` and commit
explicitly. `db/base.py` holds the `Base` (naming convention, UUIDv7 keys,
timestamps) and imports every model so autogenerate sees them.

Tests run against real PostgreSQL in their own `alloy_test` database, inside
one transaction that the fixture rolls back. `test_migrations_match_models`
diffs `upgrade head` against the models, so a model change without a
migration fails CI.

### Authentication

Sessions are opaque and server-side: a random token in an `HttpOnly`
`__Host-session` cookie, its SHA-256 in `user_sessions`. No JWTs. Passwords
are Argon2id via pwdlib, hashed off the event loop. `SameSite=Lax` plus
JSON-only bodies is the CSRF defence. Logout revokes the row rather than deleting it;
the purge job removes old rows later.

Email verification, password reset, and email change all work the same way:
an emailed link carrying a random token whose hash sits on the `users` row
until the link is followed. Signup emails a verification link
(`ALLOY_VERIFICATION_TTL`); until it is followed, everything past `/auth/*`
answers 403. A signup carrying the `invite_token` of an invitation for its
address gets no link: accepting the invitation verifies the address instead. `forgot-password` answers 204 whether or not the address exists.
A password reset revokes every session and logs the browser in. Changing the
address stores a `pending_email`, emails the new address, and notifies the
old one once swapped. Deleting an account stamps `deleted_at`, revokes every
session, and the purge job removes it after `ALLOY_ACCOUNT_DELETION_GRACE`
(default 7 days); logging in before then brings it back. It is refused while
the user is the sole owner of a workspace that has other members.

### Rate limits

`integrations/ratelimit/` keeps fixed-window counters in the database (an
unlogged table, one upsert per hit; in memory for the tests) and answers 429
with `Retry-After`. A `Limit` names the policy; the subject
(client address, email, user) picks the counter. Routes attach
`per_ip(limit)` or call the `Limiter` themselves; the `Limit`s sit next to
the routes that use them.

| Endpoint                                                | Subject         | Limit         |
| ------------------------------------------------------- | --------------- | ------------- |
| `POST /auth/login`                                      | address         | 20 per 15 min |
| `POST /auth/login`                                      | email, failures | 10 per 15 min |
| `POST /auth/signup`, `/auth/forgot-password`            | address         | 10 per hour   |
| `POST /auth/forgot-password`                            | email           | 3 per hour    |
| `POST /auth/resend-verification`, `/auth/change-email`  | user            | 3 per hour    |
| token endpoints (`verify-email`, `reset-password`, ...) | address         | 10 per minute |
| `POST /invites/{token}/accept`                          | user            | 10 per minute |
| `POST .../invites`, `.../invites/{id}/resend`           | user            | 20 per hour   |
| `POST .../assistant/conversations/{id}/messages`        | user            | 60 per hour   |

The client address is `request.client`, which Uvicorn fills from
`X-Forwarded-For` for peers in `FORWARDED_ALLOW_IPS`; the web app's proxy
route sets that header to the visitor's address (see Deploying).

### Workspaces, roles, and invitations

Every business record belongs to a workspace, reached through a seat in
`workspace_members` with one of four roles. Signing up creates no workspace:
the web app's onboarding asks for one (`POST /workspaces/`, then the setup
steps, then `POST /workspaces/{id}/onboarding/complete`, which stamps
`onboarded_at`), unless the user accepts an invitation first.

| Role   | Permissions                                                                   |
| ------ | ----------------------------------------------------------------------------- |
| owner  | everything, including `workspace:delete`                                      |
| admin  | `crm:read`, `crm:write`, `members:read`, `members:manage`, `workspace:manage` |
| member | `crm:read`, `crm:write`, `members:read`                                       |
| viewer | `crm:read`, `members:read`                                                    |

Handlers never ask for a role: they take a `Can*` dependency from
`workspaces/dependencies.py`, which loads the caller's membership (404 for
non-members, so ids leak nothing) and answers 403 when the role lacks the
permission. Owners manage everyone, others only roles below their own, and a
workspace always keeps at least one owner. Invitations are emailed links
(`ALLOY_INVITE_TTL`, default 7 days) that only the invited address can
accept; the token's hash is stored and the row is stamped, not deleted.

### Email and object storage

Both are ports in `integrations/`. `Mailer` has one method, `send(Email)`;
`ConsoleMailer` logs the message, which is what development and tests use.
Handlers never send directly: they queue `queue_email(session, email)`,
so only the worker holds the mailer. `ALLOY_MAIL_PROVIDER` picks the implementation.

`ObjectStore` has `put`, `get`, `head`, `delete`, `delete_prefix`,
`upload_url`, and `download_url`. `S3ObjectStore` (aiobotocore) is the only
implementation because every candidate speaks S3: RustFS locally, then AWS
S3, R2, or any compatible service. `MemoryObjectStore` is the test double,
and `tests/integration/integrations/test_storage.py` runs the same contract against both.

```sh
ALLOY_STORAGE_ENDPOINT_URL=null          # AWS itself; a URL for anything S3-compatible
ALLOY_STORAGE_PUBLIC_ENDPOINT_URL=...    # only if the browser reaches storage at another address
ALLOY_STORAGE_PATH_STYLE=false           # AWS; true (default) for RustFS and MinIO
ALLOY_STORAGE_REGION / _BUCKET / _ACCESS_KEY / _SECRET_KEY
```

Bytes never pass through the API: uploads are a presigned `PUT` that pins
the declared type and size, downloads a presigned `GET`, both valid for
`ALLOY_STORAGE_URL_TTL`. Keys are `workspaces/{id}/...`, so deleting a
workspace clears its files with one `delete_prefix`. The bucket needs a
CORS rule for the web app's origin; Compose sets one for `localhost:3000`.

### Background jobs

`jobs/` runs on [Procrastinate](https://procrastinate.readthedocs.io): the
queue is a set of tables in the app's PostgreSQL, so there is no broker to
run, and a job is a row a worker takes with `SKIP LOCKED`.

| Task                 | Trigger                       | What it does                                                                            |
| -------------------- | ----------------------------- | --------------------------------------------------------------------------------------- |
| `mail.send`          | anything that emails          | hands the `Email` to the mailer; retried with backoff                                   |
| `purge.expired`      | hourly                        | removes stamped-dead rows, abandoned uploads, and failed jobs after `ALLOY_PURGE_AFTER` |
| `imports.run`        | `POST .../imports/{id}/start` | loads a CSV of contacts or companies                                                    |
| `jobs.retry_stalled` | every ten minutes             | requeues jobs whose worker stopped sending heartbeats mid-run                           |

A task is a function of `Resources` (settings, a session factory, the mailer,
the object store) and JSON arguments, registered with `task()` in
`jobs/app.py`; each has a `queue_*` helper that takes the handler's session.
The job row is written on that session's connection, before the commit, so
it is committed, or rolled back, with the rows it is about, and the worker
is notified at commit, never before: the queue is its own outbox. This
leans on the sessions running on psycopg, the connection Procrastinate
accepts; a change of driver would need another way in. A run carries the request ID and trace context it was queued with, and logs
one `alloy_server.jobs` line. `alloy-worker` (`jobs/worker.py`) runs the
jobs, `ALLOY_JOBS_CONCURRENCY` at a time, and fires the `cron` tasks; run
any number, the database keeps each tick to one run. The tests swap in
Procrastinate's in-memory connector and run a worker as soon as a job is
deferred, so a queued email is in the outbox when the handler returns.

The queue's tables come from a migration that applies Procrastinate's
schema. When bumping Procrastinate across a version that ships migrations
(`procrastinate/sql/migrations/` in the package), add an Alembic migration
that runs them; `alembic/env.py` leaves the `procrastinate_*` tables out of
autogenerate.

### CSV imports

An import is the attachment handshake with a job at the end: `POST
.../imports/` returns an upload URL for the CSV (at most
`ALLOY_IMPORT_MAX_BYTES`), the browser `PUT`s it, and `POST .../{id}/start`
queues `imports.run`. The row moves through `pending → queued → running →
done | failed` with counts and the first 100 row errors. Headers match
case-insensitively; contacts take `name, email, phone, job_title, status,
company`, companies `name, website, industry, notes`. Rows are validated as
a `POST` body would be, duplicates (contact email, company name) are
skipped, and the file is written in one transaction, so a run that dies is
simply redelivered.

### Assistant

`modules/assistant/` is one [Pydantic AI](https://pydantic.dev/docs/ai/) agent with
typed tools that call the same service functions the routes do, so it can
do nothing the UI cannot. `ALLOY_OPENAI_API_KEY` turns it on (otherwise the
endpoints answer 503); `ALLOY_AI_MODEL` and `ALLOY_AI_REASONING_EFFORT`
tune it. `integrations/ai/` owns the provider wiring (the OpenAI Responses
API today); the module owns the instructions, tools, and limits.

- The server owns the transcript (`assistant_messages`); the browser posts only
  its newest message and reads the reply as an AI SDK data stream.
- Reads always run. A single write runs at once. A delete, or a call with
  more than one item, pauses for approval: the browser shows what is about
  to happen and the run resumes on Approve or Deny. Rows the assistant
  creates carry `created_by` and `source = agent`.
- Files dropped into the chat upload with the attachment handshake; images
  and PDFs are shown to the model for that turn only. Tools can turn an
  upload into a normal attachment without copying bytes. Unattached uploads
  are purged after `ALLOY_CHAT_UPLOAD_TTL`.
- Every tool checks the membership's permission and filters by workspace;
  `UsageLimits` bound each run. Each model request is recorded in
  `model_calls` (workspace, user, model, tokens, request ID) for quotas and
  reporting. `tests/integration/modules/assistant/` drives the endpoint with
  a scripted `FunctionModel`; `evals/` runs real prompts against the live
  model on demand (`uv run python -m evals.run`).

### Tiny CRM (demo)

`crm/` is the sample application: contacts, companies, an activity feed,
tasks, attachments, imports, and a dashboard. It can be deleted as a unit.
Every row belongs to a workspace and a row from another workspace is a 404,
in the path or in a body. Lists answer with `{items, total, limit, offset}`
and take `sort` and `order`; `PATCH` bodies are partial, with `null`
clearing an optional field (a required one, such as `name`, cannot be
null). Datetimes must carry a time zone offset. Logging a call, email,
meeting, or follow-up sets the contact's `last_contacted_at`; completing a
task logs a `task_completed` activity. "Today" for tasks and the dashboard
follows the `tz` query parameter. Rows carry `created_by` and `source`
(`agent`, `import`, or null).

## packages/api-client

`@alloy/api-client`: [openapi-fetch](https://openapi-ts.dev/openapi-fetch/)
with types generated by openapi-typescript from the API's schema. Both
`openapi.json` and `src/generated/schema.ts` are committed, so consumers
need no Python and schema changes show up in review.

```ts
import { createApiClient } from "@alloy/api-client";

const api = createApiClient({ baseUrl: "http://127.0.0.1:8000" });
const { data, error } = await api.GET("/health/");
```

```sh
vp run generate           # after changing a route or model in apps/server
vp run check:generated    # fails if the committed files are stale; CI runs this
```

`exports` points at the source, so `apps/web` consumes it without a build
step. The package pins TypeScript 5 for openapi-typescript's compiler API;
the rest of the workspace is on TypeScript 7.

## apps/web

A [Next.js](https://nextjs.org/docs) 16 app, package `@alloy/web`: the
front end for the CRM and the assistant.

```text
apps/web/src/
├── proxy.ts                  # redirects on the session cookie's presence
├── app/                      # routes only; each page composes feature components behind <Suspense>
│   ├── api/[...path]/route.ts   # forwards /api/* to the API with the cookie and the visitor's address
│   ├── (auth)/                  # login, signup, and the emailed-link pages
│   └── (app)/[workspaceId]/     # sidebar layout; dashboard, contacts, companies, tasks, assistant, imports, members, settings, account
├── features/                 # product code by domain, mirroring the API: auth, workspaces, crm/*, assistant
│   └── <feature>/            # components/, hooks/, queries.ts, mutations.ts, schemas.ts, server.ts
├── components/               # ui/ (shadcn) and shared/ (layout, form, chat, data-table, ...)
├── hooks/                    # generic hooks
└── lib/                      # infrastructure: api/, auth/session.ts, formatting/, time-zone/, lists.ts, validation.ts, routes.ts
```

The browser only talks to Next.js: `API_URL` is read on the server and the
proxy route forwards `/api/*` with the session cookie, so one build serves
any environment and the API needs no CORS. `apps/web/README.md` covers how
pages split between Server and Client Components, how data flows through
TanStack Query, and how forms and tables are built.

Configuration worth knowing: `cacheComponents` (static shell, dynamic parts
behind `<Suspense>`), `typedRoutes`, `reactCompiler`, and
`skipTrailingSlashRedirect` (the API's collection routes end in a slash).
Tailwind v4 and shadcn/ui on Base UI. No ESLint: oxlint via `vp check`
covers it. Tests run under Vitest with the `@/` alias from
`apps/web/vite.config.ts`.

## Deploying

The template does not pick a host. It ships an image per app, one command
per process, settings from environment variables, and a migration step.

| Process  | Image         | Command                                             | Port | Instances |
| -------- | ------------- | --------------------------------------------------- | ---- | --------- |
| `api`    | `apps/server` | `fastapi run --port 8000 --proxy-headers` (default) | 8000 | any       |
| `worker` | `apps/server` | `alloy-worker`                                      | none | any       |
| `web`    | `apps/web`    | `node apps/web/server.js` (default)                 | 3000 | any       |

Plus managed PostgreSQL and an S3-compatible bucket the browser can reach.
Only `web` needs a public address; it forwards `/api/*` to the API over the
private network. Give `api` a health check on `/health/`
(`/health/{db,storage}` for readiness). Run `alembic upgrade head`
from `/app/apps/server` before new code starts (a pre-deploy command, release
command, or init container); migrations are written to be safe to apply
before the old code stops.

`CLIENT_IP_HEADER` names the one request header the platform in front of
`web` overwrites with the visitor's address (`cf-connecting-ip`,
`x-real-ip`, `x-forwarded-for`); the proxy route passes it upstream and the
API's rate limits count against it. Unset, every request counts against
`web`'s own address. The API image sets `FORWARDED_ALLOW_IPS=*`, which is
safe while only `web` can reach it.

Every process reads the same `ALLOY_*` variables, documented in
`apps/server/.env.example`; `web` reads `API_URL` and `CLIENT_IP_HEADER`. The
ones that change per environment:

```sh
ALLOY_DATABASE_URL=postgresql+psycopg://...
ALLOY_STORAGE_ENDPOINT_URL=... ALLOY_STORAGE_BUCKET=... ALLOY_STORAGE_ACCESS_KEY=... ALLOY_STORAGE_SECRET_KEY=...
ALLOY_STORAGE_PATH_STYLE=false                   # true for MinIO and RustFS
ALLOY_FRONTEND_URL=https://app.example.com       # links in emails
ALLOY_LOGFIRE_TOKEN=...                          # optional
ALLOY_OPENAI_API_KEY=...                         # optional; empty turns the assistant off
API_URL=http://api.internal:8000                 # web only
CLIENT_IP_HEADER=x-forwarded-for                 # web only
```

`.github/workflows/images.yml` builds `ghcr.io/<owner>/<repo>/{server,web}`
after CI passes on `main`, tagged `latest` and `sha-<short sha>`, for hosts
that pull from a registry. On Railway, four services from one repository
with the Dockerfile paths and commands above, `alembic upgrade head` as the
pre-deploy command on `api`, and `API_URL=http://api.railway.internal:8000`.
Email is still the console mailer until a provider is added.

## Supply-chain policy

`pnpm-workspace.yaml`: `minimumReleaseAge` of 4 days, `strictDepBuilds` with
an empty `allowBuilds`, `blockExoticSubdeps`, `trustPolicy: no-downgrade`,
`verifyDepsBeforeRun`, `engineStrict`. `pyproject.toml`: `exclude-newer` of
4 days and `required-version` for uv. CI uses least-privilege permissions,
SHA-pinned actions, and frozen lockfiles; Dependabot runs weekly with a
matching 4-day cooldown.

## License

[MIT](LICENSE) © builtbystef
