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

/** Deduplicated per request, so the layout and the page share one call. */
export const getCurrentUser = cache(async (): Promise<UserRead | null> => {
  const api = await getSessionApi();
  const result = await api.GET("/auth/me");
  if (result.data) return result.data;
  if (result.response.status === 401) return null;
  throw ApiError.fromResult(result);
});

export async function requireUser(): Promise<UserRead> {
  const user = await getCurrentUser();
  if (user === null) redirect("/login");
  return user;
}

export async function listWorkspaces(): Promise<WorkspaceRead[]> {
  await requireUser();
  const api = await getSessionApi();
  const result = await api.GET("/workspaces/");
  if (result.data) return result.data;
  throw ApiError.fromResult(result);
}

/** Null for non-members too: the API answers 404 either way. Deduplicated per request. */
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

export async function requireWorkspace(workspaceId: string): Promise<WorkspaceRead> {
  const workspace = await getWorkspace(workspaceId);
  if (workspace === null) notFound();
  return workspace;
}
