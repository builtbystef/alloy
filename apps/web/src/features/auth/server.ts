import "server-only";

import type { ApiClient, UserResponse } from "@alloy/api-client";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { cache } from "react";

import { ApiError } from "@/lib/api/errors";
import { createApi } from "@/lib/api/server-client";

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

/** Deduplicated per request, so the layout and the page share one call. */
export const getCurrentUser = cache(async (): Promise<UserResponse | null> => {
  const api = await getSessionApi();
  const result = await api.GET("/auth/me");
  if (result.data) return result.data;
  if (result.response.status === 401) return null;
  throw ApiError.fromResult(result);
});

/**
 * Logged in and verified: what every app page needs. A cookie the API rejects
 * goes through `/logout`, which clears it; `/login` alone would bounce back
 * here for as long as the cookie is present.
 */
export async function requireUser(): Promise<UserResponse> {
  const user = await getCurrentUser();
  if (user === null) redirect("/logout");
  if (user.email_verified_at === null) redirect("/verify-email");
  return user;
}
