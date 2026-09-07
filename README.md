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
- Docker with Compose, for the local PostgreSQL that `apps/api` and its tests use

## Commands

The root `package.json` scripts cover both languages:

```sh
vp run check        # format + lint + typecheck, both languages
vp run check:fix
vp run test         # Vitest + pytest
vp run build
vp run ci           # everything CI runs
vp run db:up        # PostgreSQL in Docker, waits until it accepts connections
vp run db:migrate   # apply pending Alembic migrations
vp run db:down      # stop PostgreSQL (data is kept; add --volumes to wipe it)
vp run dev:api      # FastAPI with reload, http://127.0.0.1:8000
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
├── pyproject.toml            # fastapi, pydantic-settings, sqlalchemy, psycopg, alembic, pwdlib; [tool.alembic]
├── compose.yaml              # local PostgreSQL 18
├── alembic.ini               # Alembic logging only
├── alembic/                  # env.py (async, URL from Settings), script.py.mako, versions/
├── .env.example
├── src/alloy_api/
│   ├── main.py               # app, lifespan (database engine), CORS, router includes
│   ├── config.py             # Settings (pydantic-settings) + get_settings dependency
│   ├── db.py                 # engine, session factory, get_session / SessionDep
│   ├── models.py             # declarative Base, naming convention, id/timestamp mixins; imports every model
│   ├── routers/health.py     # GET /health/ (liveness), GET /health/db (readiness)
│   ├── auth/                 # sign up, log in, log out; cookie sessions in Postgres; CurrentUserDep
│   └── crm/                  # the Tiny CRM demo: companies, contacts, activities, tasks, dashboard
└── tests/                    # TestClient fixture: settings overridden, one rolled-back transaction
```

```sh
vp run dev:api                # fastapi dev, reloads on change, http://127.0.0.1:8000/docs
cd apps/api && uv run fastapi run   # production server, no reload, 0.0.0.0
```

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

### Database

PostgreSQL 18 runs in Docker from `apps/api/compose.yaml`, with
[SQLAlchemy](https://docs.sqlalchemy.org) 2 in async mode over
[psycopg 3](https://www.psycopg.org/psycopg3/docs/) and
[Alembic](https://alembic.sqlalchemy.org) for migrations:

```sh
vp run db:up                  # start PostgreSQL, waits until healthy (127.0.0.1:5432, alloy/alloy)
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
old sessions are kept until you prune them
(`DELETE FROM user_sessions WHERE revoked_at IS NOT NULL OR expires_at < now()`).

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

### Tiny CRM (demo)

`crm/` is a sample application on top of the template: contacts, companies,
an activity feed per contact, tasks, and a dashboard, for freelancers and
small teams. It exists to show the setup end to end and can be deleted as a
unit (the package, its migration, its tests, and two lines in `main.py`).

Every row is owned by a user (`OwnedByUser` mixin), every query filters on
the caller, and a row that belongs to someone else is a 404, whether it is
addressed in the path or referenced from a body (`company_id`, `contact_id`).
Lists take `limit` (≤ 500) and `offset`. `PATCH` bodies are partial: a field
left out is untouched, a field sent as `null` is cleared.

```text
GET/POST          /companies/                    ?q=            search name, website, industry
GET/PATCH/DELETE  /companies/{id}                               delete keeps contacts and tasks, clears the link
GET               /companies/{id}/contacts

GET/POST          /contacts/                     ?q= &status= &company_id=
GET/PATCH/DELETE  /contacts/{id}                                delete removes the activity feed, keeps tasks
GET/POST          /contacts/{id}/activities                     newest first

GET/POST          /tasks/                        ?due=overdue|today|upcoming &tz= &status= &contact_id= &company_id=
GET/PATCH/DELETE  /tasks/{id}

GET               /dashboard/                    ?tz= &stale_days=30 &limit=5
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
and contacts, companies, and tasks.

```text
apps/web/
├── package.json              # next, react; @alloy/api-client; zod; @tanstack/react-{query,form,table}; tailwindcss; @base-ui/react, lucide-react, sonner
├── next.config.ts            # cacheComponents, typedRoutes, reactCompiler, skipTrailingSlashRedirect
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
    │   └── (app)/                      # sidebar layout with nav + user menu; dashboard, contacts, companies, tasks, settings
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
