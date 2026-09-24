import type { ApiClient } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { workspaceKeys } from "@/features/workspaces/queries";
import { unwrap } from "@/lib/api/errors";

/** Under the workspace keys, so `invalidateWorkspaces` drops these too. */
export const inviteKeys = {
  list: (ws: string) => [...workspaceKeys.detail(ws), "invites"] as const,
  /** The caller's own, across workspaces. */
  pending: () => [...workspaceKeys.all, "pending"] as const,
};

export function inviteListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: inviteKeys.list(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/invites", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

export function pendingInviteListQuery(api: ApiClient) {
  return queryOptions({
    queryKey: inviteKeys.pending(),
    queryFn: async () => unwrap(await api.GET("/invites/pending")),
  });
}
