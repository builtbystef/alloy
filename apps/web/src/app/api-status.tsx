import { api } from "@/lib/api";

/**
 * Reads the API's health endpoint on every request. It is not cached, so the
 * page renders it behind <Suspense> and streams the result in.
 */
export async function ApiStatus() {
  try {
    const { data, error, response } = await api.GET("/health/");
    if (data === undefined) {
      return (
        <p>
          API returned HTTP {response.status}: <code>{JSON.stringify(error)}</code>
        </p>
      );
    }
    return (
      <p>
        API status: <strong>{data.status}</strong>
      </p>
    );
  } catch (cause) {
    // Network failure, typically the API is not running. openapi-fetch
    // rejects here instead of returning an error body.
    const message = cause instanceof Error ? cause.message : String(cause);
    return (
      <p>
        API unreachable: <code>{message}</code>
      </p>
    );
  }
}
