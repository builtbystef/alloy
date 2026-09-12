import type { ApiClient } from "@alloy/api-client";
import { queryOptions, type QueryClient } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";

/**
 * Shared by server prefetches and client reads, which must build the same
 * key: that is why the client is a parameter rather than an import.
 */

export const workspaceKeys = {
  all: ["workspaces"] as const,
  list: () => [...workspaceKeys.all, "list"] as const,
  detail: (id: string) => [...workspaceKeys.all, "detail", id] as const,
  members: (id: string) => [...workspaceKeys.detail(id), "members"] as const,
  invites: (id: string) => [...workspaceKeys.detail(id), "invites"] as const,
};

export function workspaceListQuery(api: ApiClient) {
  return queryOptions({
    queryKey: workspaceKeys.list(),
    queryFn: async () => unwrap(await api.GET("/workspaces/")),
  });
}

export function memberListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: workspaceKeys.members(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/members", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

export function inviteListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: workspaceKeys.invites(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/invites", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

/** Drop the workspace list, members, and invitations after a membership change. */
export async function invalidateWorkspaces(queryClient: QueryClient): Promise<void> {
  await queryClient.invalidateQueries({ queryKey: workspaceKeys.all });
}
