# apps/server

The FastAPI app, the Procrastinate worker, and the assistant agent (Python package `alloy_server`).

```sh
vp run dev:api       # from the repo root, http://127.0.0.1:8000/docs
vp run dev:worker    # the job worker, restarted on changes
```

```text
apps/server/
├── src/alloy_server/
│   ├── asgi.py           # entry point for `fastapi run`/`fastapi dev`
│   ├── main.py           # create_app(settings): the API and its lifespan
│   ├── config.py         # Settings; every ALLOY_* variable is documented in .env.example
│   ├── resources.py      # what every process opens once: database, mailer, store, queue
│   ├── modules/          # one package per feature: auth, workspaces (+ invites/), crm/*, assistant, health
│   │   └── <feature>/    # router.py, schemas.py, models.py, service.py, dependencies.py
│   ├── integrations/     # ports with their adapters: mail, storage, ai, rate_limit
│   ├── jobs/             # the worker, the task registry, and platform tasks (purge, stalled)
│   ├── db/               # declarative base, session, and models.py, which imports every model
│   └── shared/           # AppError and subclasses, middleware, logs, telemetry
├── alembic/              # migrations
├── evals/                # assistant evals, run by hand
└── tests/
    ├── unit/
    └── integration/      # real PostgreSQL, one rolled-back transaction per test
```

## Rules the code relies on

- **One place for the work.** A module's `service.py` does the work and raises `AppError`s. Routes, the assistant's tools, and the worker's jobs all call the same service functions; none holds logic of its own.
- **No repository layer.** Services take the session; the session is the unit of work.
- **Narrow imports between modules.** A module imports another only through its `service`, `models`, and `dependencies`.
- **Workspace scoping.** Every record belongs to a workspace. Every handler takes a `Can*` dependency (`CanReadCrm`, `CanManageMembers`, ...): 404 for non-members, 403 without the permission.
- **The environment is read in two places.** Only `asgi.py` and `jobs/worker.py` read it. Everything else, tests included, receives a `Settings`.
- **Jobs commit with their data.** A job is queued on the handler's session, so it commits or rolls back with the rows it is about.
- **Tests never call the model.** The test settings drop the OpenAI key.

## Adding things

- **A model**: import its module in `db/models.py` so Alembic sees it, then add a migration: `uv run alembic revision --autogenerate -m "..."` from `apps/server`. CI fails on a model without a migration.
- **A route, or a change to request or response shapes**: run `vp run generate` from the root to regenerate the typed client.
- **A job**: put it in a `jobs.py` next to what it works on, register it with `task()`, and list the module in `TASK_MODULES` in `jobs/__init__.py`.
- **A setting**: add it to `Settings` and document it in `.env.example`.
- **A Procrastinate upgrade**: if the new version ships SQL migrations (`procrastinate/sql/migrations/` in the package), add an Alembic migration that runs them. `alembic/env.py` leaves the `procrastinate_*` tables out of autogenerate.

## How it works

- **Errors and logs**: every response and log line carries `X-Request-ID`. Unhandled exceptions become a plain 500.
- **Database**: SQLAlchemy 2 async over psycopg 3, migrations with Alembic.
- **Auth**: opaque server-side sessions in an `HttpOnly` `__Host-session` cookie, Argon2id passwords, and emailed links for verification, reset, and email change. Deleted accounts are purged after `ALLOY_ACCOUNT_DELETION_GRACE`.
- **Rate limits**: fixed-window counters in the database, 429 with `Retry-After`. Each `Limit` sits next to the routes that use it.
- **Workspaces**: roles are owner, admin, member, and viewer. Invitations are emailed links.
- **Email and storage**: email is queued and sent by the worker (a console mailer by default). Storage is S3-compatible (RustFS locally); uploads and downloads use presigned URLs under `workspaces/{id}/...`.
- **Jobs**: [Procrastinate](https://procrastinate.readthedocs.io) on the app's PostgreSQL, with no broker.
- **Assistant**: one [Pydantic AI](https://pydantic.dev/docs/ai/) agent over the CRM services, turned on by `ALLOY_OPENAI_API_KEY`. Reads run freely, single writes run at once, and deletes and bulk calls pause for approval. Every model call is recorded in `model_calls`.
- **CRM**: the demo (contacts, companies, tasks, attachments, CSV imports, dashboard), deletable as a unit.
