import type { ApiClient } from "@alloy/api-client";
import { queryOptions } from "@tanstack/react-query";

import { unwrap } from "@/lib/api/errors";

/** The assistant's conversations: the caller's own, per workspace. */
export const conversationKeys = {
  all: ["conversations"] as const,
  list: (ws: string) => [...conversationKeys.all, ws, "list"] as const,
  detail: (ws: string, id: string) => [...conversationKeys.all, ws, "detail", id] as const,
};

/** Most recently active first. */
export function conversationListQuery(api: ApiClient, ws: string) {
  return queryOptions({
    queryKey: conversationKeys.list(ws),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/agent/conversations", {
          params: { path: { workspace_id: ws } },
        }),
      ),
  });
}

/** One conversation with its transcript as AI SDK messages. */
export function conversationQuery(api: ApiClient, ws: string, id: string) {
  return queryOptions({
    queryKey: conversationKeys.detail(ws, id),
    queryFn: async () =>
      unwrap(
        await api.GET("/workspaces/{workspace_id}/agent/conversations/{conversation_id}", {
          params: { path: { workspace_id: ws, conversation_id: id } },
        }),
      ),
  });
}
