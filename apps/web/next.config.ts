import type { NextConfig } from "next";

import path from "node:path";

const nextConfig: NextConfig = {
  // Routes prerender a static shell; uncached reads stream behind <Suspense>.
  cacheComponents: true,
  typedRoutes: true,
  // Memoizes automatically; manual useMemo/useCallback only where precise control is needed.
  reactCompiler: true,
  // The FastAPI collection routes end in a slash (`/contacts/`). Without this,
  // Next.js would 308 `/api/contacts/` to `/api/contacts` before the proxy
  // route handler in src/app/api/[...path] could forward it.
  skipTrailingSlashRedirect: true,
  // apps/web/Dockerfile copies .next/standalone: a server.js plus only the
  // files it traced. The tracing root is the monorepo root, so workspace
  // packages (@alloy/api-client) and hoisted node_modules are included.
  output: "standalone",
  outputFileTracingRoot: path.join(import.meta.dirname, "../.."),
};

export default nextConfig;
