import "server-only";

import type { ApiClient, UserRead } from "@alloy/api-client";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { createApi } from "./api";
import { ApiError } from "./api-error";

/** The API's session cookie; see auth/cookies.py. */
export const SESSION_COOKIE = "__Host-session";

/**
 * A client that forwards the caller's session cookie, for Server Components.
 * Reading `cookies()` is request-time work, so callers sit behind <Suspense>.
 */
export async function getSessionApi(): Promise<ApiClient> {
  const token = (await cookies()).get(SESSION_COOKIE)?.value;
  return createApi(globalThis.fetch, token ? { cookie: `${SESSION_COOKIE}=${token}` } : undefined);
}

/** The logged-in user, or null. Deduplicated per request across layout and page. */
export const getCurrentUser = cache(async (): Promise<UserRead | null> => {
  const api = await getSessionApi();
  const result = await api.GET("/auth/me");
  if (result.data) return result.data;
  if (result.response.status === 401) return null;
  throw ApiError.fromResult(result);
});

/** The logged-in user; sends anyone else to the login page. */
export async function requireUser(): Promise<UserRead> {
  const user = await getCurrentUser();
  if (user === null) redirect("/login");
  return user;
}
