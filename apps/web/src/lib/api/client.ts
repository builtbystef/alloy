import { createApiClient, type ApiClient } from "@alloy/api-client";

/**
 * The typed client for Client Components. It talks to the proxy route handler
 * in `src/app/api/[...path]`, which forwards to the API with the session
 * cookie; being same-origin, the browser attaches the cookie by itself.
 */
export const browserApi: ApiClient = createApiClient({ baseUrl: "/api" });
