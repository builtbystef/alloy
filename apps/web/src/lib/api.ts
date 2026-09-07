import { createApiClient, type ApiClient, type ClientOptions } from "@alloy/api-client";

/**
 * Where the API lives. Read from the server-side environment, so it is never
 * inlined into the browser bundle and can differ per deployment at runtime.
 */
export function getApiUrl(): string {
  return process.env["API_URL"] ?? "http://127.0.0.1:8000";
}

/**
 * The typed client for apps/api, for use in Server Components, Route
 * Handlers, and Server Actions. Requests are memoized per render by Next.js's
 * `fetch`, so calling this in several components costs one request.
 *
 * Pass `headers` to forward the caller's session cookie; `getSessionApi()` in
 * `session.ts` does that from `cookies()`.
 */
export function createApi(
  fetch: typeof globalThis.fetch = globalThis.fetch,
  headers?: ClientOptions["headers"],
): ApiClient {
  return createApiClient({ baseUrl: getApiUrl(), fetch, ...(headers ? { headers } : {}) });
}

export const api: ApiClient = createApi();
