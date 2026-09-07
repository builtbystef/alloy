import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cache Components: routes prerender a static shell, `use cache` opts data
  // into the cache, and uncached reads stream behind <Suspense>.
  cacheComponents: true,
  // Type-checks <Link href> and router.push() against the real routes.
  typedRoutes: true,
  // React Compiler (babel-plugin-react-compiler): memoizes components and
  // values automatically, so manual useMemo/useCallback is only for cases
  // that need precise control. Next.js runs it only on files with JSX or hooks.
  reactCompiler: true,
  // The FastAPI collection routes end in a slash (`/contacts/`). Without this,
  // Next.js would 308 `/api/contacts/` to `/api/contacts` before the proxy
  // route handler in src/app/api/[...path] could forward it.
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
