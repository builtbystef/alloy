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
pnpm check          # format + lint + typecheck, both languages
pnpm check:fix
pnpm test           # Vitest + pytest
pnpm build          # vp run -r build
pnpm run ci         # everything CI runs (plain `pnpm ci` is a clean install)
```

Each language is also available on its own:

```sh
vp install          # install Node dependencies
vp add / remove     # change Node dependencies
vp check [--fix]    # oxfmt + oxlint + tsc          (pnpm check:ts)
vp test             # Vitest                         (pnpm test:ts)
vp run -r build     # dependency-aware, cached task runner

uv sync --all-packages   # create .venv, install every Python project
uv add / remove          # change Python dependencies (run inside the project)
uv run ruff format .     # format                     (pnpm check:py)
uv run ruff check .      # lint
uv run ty check          # type check
uv run pytest            # tests                      (pnpm test:py)
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

`uv init --lib packages/core-py` (or `--app`) scaffolds a member with a
`src/<package>/` layout and the `uv_build` backend. Put tests in `tests/`.
Ruff, ty, and pytest read their settings from the root `pyproject.toml`, and
the tools themselves are a root-level dependency group, so a member declares
only its own metadata and runtime dependencies.

## Supply-chain policy

Defined in `pnpm-workspace.yaml`:

- `minimumReleaseAge: 5760`: new versions must be ≥ 4 days old before resolving
- `strictDepBuilds` + `allowBuilds: {}`: no dependency runs lifecycle scripts
  until explicitly reviewed and listed
- `blockExoticSubdeps`: transitive deps must come from the registry
- `trustPolicy: no-downgrade`: publisher trust levels may not regress
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
