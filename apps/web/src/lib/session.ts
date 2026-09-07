import "server-only";

import type { ApiClient, UserRead, WorkspaceRead } from "@alloy/api-client";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";
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

/** Every workspace the logged-in user belongs to. */
export async function listWorkspaces(): Promise<WorkspaceRead[]> {
  await requireUser();
  const api = await getSessionApi();
  const result = await api.GET("/workspaces/");
  if (result.data) return result.data;
  throw ApiError.fromResult(result);
}

/**
 * The workspace from the URL, with the caller's role and permissions, or null
 * when they are not a member (the API answers 404 either way). Deduplicated
 * per request, so the layout and the page share one call.
 */
export const getWorkspace = cache(async (workspaceId: string): Promise<WorkspaceRead | null> => {
  const api = await getSessionApi();
  const result = await api.GET("/workspaces/{workspace_id}", {
    params: { path: { workspace_id: workspaceId } },
  });
  if (result.data) return result.data;
  if (result.response.status === 401) redirect("/login");
  if (result.response.status === 404 || result.response.status === 422) return null;
  throw ApiError.fromResult(result);
});

/** The workspace from the URL; logged-out users go to `/login`, non-members get a 404. */
export async function requireWorkspace(workspaceId: string): Promise<WorkspaceRead> {
  const workspace = await getWorkspace(workspaceId);
  if (workspace === null) notFound();
  return workspace;
}
