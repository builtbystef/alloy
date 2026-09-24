import "server-only";

import type { ConversationResponse } from "@alloy/api-client";

import { getSessionApi } from "@/features/auth/server";
import { conversationListQuery } from "@/features/assistant/queries";
import { unwrap } from "@/lib/api/errors";
import { getQueryClient } from "@/lib/query-client";

/**
 * The most recent conversation, or a new one when there is none. The API
 * reuses an empty conversation, so landing on `/assistant` twice does not
 * pile them up.
 */
export async function latestConversation(workspaceId: string): Promise<ConversationResponse> {
  const api = await getSessionApi();
  const [latest] = await getQueryClient().query(conversationListQuery(api, workspaceId));
  if (latest) return latest;
  return unwrap(
    await api.POST("/workspaces/{workspace_id}/assistant/conversations", {
      params: { path: { workspace_id: workspaceId } },
    }),
  );
}
