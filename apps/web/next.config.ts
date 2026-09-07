import type { NextConfig } from "next";

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
};

export default nextConfig;
