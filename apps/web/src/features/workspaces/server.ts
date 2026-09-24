import "server-only";

import type { WorkspaceResponse } from "@alloy/api-client";
import { notFound, redirect } from "next/navigation";
import { cache } from "react";

import { ApiError } from "@/lib/api/errors";
import { getSessionApi, requireUser } from "@/features/auth/server";

/** The caller's workspaces, for Server Components. */
export async function listWorkspaces(): Promise<WorkspaceResponse[]> {
  await requireUser();
  const api = await getSessionApi();
  const result = await api.GET("/workspaces/");
  if (result.data) return result.data;
  throw ApiError.fromResult(result);
}

/** Null for non-members too: the API answers 404 either way. Deduplicated per request. */
export const getWorkspace = cache(
  async (workspaceId: string): Promise<WorkspaceResponse | null> => {
    const api = await getSessionApi();
    const result = await api.GET("/workspaces/{workspace_id}", {
      params: { path: { workspace_id: workspaceId } },
    });
    if (result.data) return result.data;
    if (result.response.status === 401) redirect("/logout");
    // The API answers 403 here only for an unverified email; roles produce 404.
    if (result.response.status === 403) redirect("/verify-email");
    if (result.response.status === 404 || result.response.status === 422) return null;
    throw ApiError.fromResult(result);
  },
);

export async function requireWorkspace(workspaceId: string): Promise<WorkspaceResponse> {
  const workspace = await getWorkspace(workspaceId);
  if (workspace === null) notFound();
  return workspace;
}
