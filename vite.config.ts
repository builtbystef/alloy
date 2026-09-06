import { defineConfig } from "vite-plus";

export default defineConfig({
  staged: {
    "*": "vp check --fix",
  },
  // Agent tooling (skills, local settings) is vendored content, not project
  // source. Formatting it is noise, and it must not fail CI if committed.
  fmt: {
    ignorePatterns: ["**/.agents/**", "**/.claude/**"],
  },
  lint: {
    plugins: ["typescript"],
    options: {
      typeAware: true,
      typeCheck: true,
    },
    ignorePatterns: ["**/dist/**", "**/coverage/**", "**/.agents/**", "**/.claude/**"],
    overrides: [
      {
        // `plugins` in an override replaces the base list, so repeat it.
        files: ["**/*.test.ts", "**/*.spec.ts"],
        plugins: ["typescript", "vitest"],
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
