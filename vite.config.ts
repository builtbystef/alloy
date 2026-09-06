import { defineConfig } from "vite-plus";

export default defineConfig({
  staged: {
    "*": "vp check --fix",
    "*.py": ["uv run ruff check --fix", "uv run ruff format"],
  },
  // Vendored agent tooling. Excluded here, not only via .gitignore, so it never
  // fails checks if it is committed.
  fmt: {
    ignorePatterns: ["**/.agents/**", "**/.claude/**"],
  },
  lint: {
    options: {
      typeAware: true,
      typeCheck: true,
    },
    ignorePatterns: ["**/dist/**", "**/coverage/**", "**/.agents/**", "**/.claude/**"],
    overrides: [
      {
        files: ["**/*.test.ts", "**/*.spec.ts"],
        plugins: ["vitest"],
      },
    ],
  },
  test: {
    passWithNoTests: true,
  },
  pack: {
    dts: true,
    sourcemap: true,
  },
  run: {
    cache: true,
  },
});
