# Alloy

An opinionated template for creating web apps using Typescript + Next.js and Python + FastAPI.

Extending carbon-fiber template (https://github.com/builtbystef/carbon-fiber)

A TypeScript template for any kind of project: apps, libraries,
CLIs, services. [Vite+](https://viteplus.dev) (`vp`) handles dependencies, formatting, linting, type checking, tests, and builds.

## Requirements

- Node ≥ 24 (pinned in `.node-version`, enforced at install)

## Commands

```sh
vp install          # install dependencies
vp add / remove     # change dependencies
vp check            # format + lint + typecheck in one pass
vp check --fix
vp test             # Vitest
vp run -r build     # dependency-aware, cached task runner
vp run ci           # everything CI runs
```

A pre-commit hook (`.vite-hooks/`) runs `vp check --fix` on staged files.
Only the hook itself is tracked; the shims and `core.hooksPath` are local to
each clone, so run `vp config` once after cloning to activate it.

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

## Supply-chain policy

Defined in `pnpm-workspace.yaml`:

- `minimumReleaseAge: 5760`: new versions must be ≥ 4 days old before resolving
- `strictDepBuilds` + `allowBuilds: {}`: no dependency runs lifecycle scripts
  until explicitly reviewed and listed
- `blockExoticSubdeps`: transitive deps must come from the registry
- `trustPolicy: no-downgrade`: publisher trust levels may not regress
- `verifyDepsBeforeRun`: scripts never run against a stale tree
- `engineStrict`: Node version mismatch fails instead of warning

CI (`.github/workflows/ci.yml`) uses least-privilege permissions, SHA-pinned
actions, and a frozen lockfile. Dependabot runs weekly with a 4-day cooldown
matching `minimumReleaseAge`.

## License

[MIT](LICENSE) © builtbystef
