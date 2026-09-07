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

## Commands

The root `package.json` scripts cover both languages:

```sh
vp run check        # format + lint + typecheck, both languages
vp run check:fix
vp run test         # Vitest + pytest
vp run build
vp run ci           # everything CI runs
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
├── pyproject.toml            # fastapi[standard-no-fastapi-cloud-cli], pydantic-settings
├── .env.example
├── src/alloy_api/
│   ├── main.py               # app, CORS, router includes
│   ├── config.py             # Settings (pydantic-settings) + get_settings dependency
│   └── routers/health.py     # GET /health/
└── tests/                    # TestClient fixture with settings overridden
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
package `@alloy/web`:

```text
apps/web/
├── package.json              # next, react, react-dom; @alloy/api-client; tailwindcss; @base-ui/react, cn, lucide-react
├── next.config.ts            # cacheComponents, typedRoutes, reactCompiler
├── postcss.config.mjs        # @tailwindcss/postcss
├── components.json           # shadcn/ui config: base-nova style, zinc, src/app/globals.css
├── tsconfig.json             # tsconfig/browser.json + jsx, paths (@/*), next plugin
├── .env.example              # API_URL
└── src/
    ├── app/                  # routes: layout.tsx, page.tsx, globals.css (Tailwind + theme tokens)
    │   └── api-status.tsx    # awaits api.GET("/health/") behind <Suspense>
    ├── components/ui/        # shadcn/ui components, added with `pnpm dlx shadcn@latest add`
    └── lib/api.ts            # createApiClient({ baseUrl: process.env.API_URL })
```

```sh
vp run dev:web                # next dev, http://localhost:3000
cd apps/web && vp run build   # next build (part of vp run -r build)
cd apps/web && vp run start   # production server
cd apps/web && vp run typegen # regenerate next-env.d.ts and .next/types without a build
```

`src/lib/api.ts` builds the `@alloy/api-client` instance from `API_URL`
(default `http://127.0.0.1:8000`). It is a server-only variable, no
`NEXT_PUBLIC_` prefix, so the browser never calls the API directly and one build
can target a different API per environment. Copy `.env.example` to `.env.local`
to change it; `.env*` is gitignored except the example.

Choices worth knowing, all from the Next.js 16 docs:

- `cacheComponents: true`: the current caching model. Routes prerender a static
  shell; uncached reads go behind `<Suspense>` and stream, or opt in with
  `"use cache"`. `next build` reports `/` as Partial Prerender.
- `typedRoutes: true`: `<Link href>` and `router.push()` are checked against the
  routes generated in `.next/types`.
- `reactCompiler: true`: the React Compiler memoizes components and values
  automatically, so write plain React and reach for `useMemo`/`useCallback`
  only for precise control, as the React docs advise. It runs as
  `babel-plugin-react-compiler` on files with JSX or hooks only. The
  Babel-free `experimental.turbopackRustReactCompiler` exists but is not yet
  recommended for production.
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
