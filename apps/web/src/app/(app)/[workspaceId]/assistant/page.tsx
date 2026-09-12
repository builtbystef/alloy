import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { unwrap } from "@/lib/api/errors";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";

import { ChatSkeleton } from "@/features/assistant/components/chat-skeleton";

export const metadata: Metadata = { title: "Assistant" };

type Params = Promise<{ workspaceId: string }>;

/**
 * `/assistant` opens the most recent conversation, or starts one. The API
 * reuses an empty conversation, so landing here twice does not pile them up.
 */
export default function AssistantPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<ChatSkeleton />}>
      <OpenLatest params={params} />
    </Suspense>
  );
}

async function OpenLatest({ params }: { params: Params }): Promise<never> {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const api = await getSessionApi();
  const conversations = unwrap(
    await api.GET("/workspaces/{workspace_id}/agent/conversations", {
      params: { path: { workspace_id: workspaceId } },
    }),
  );
  const target =
    conversations[0] ??
    unwrap(
      await api.POST("/workspaces/{workspace_id}/agent/conversations", {
        params: { path: { workspace_id: workspaceId } },
      }),
    );
  redirect(workspacePaths(workspaceId).assistantChat(target.id));
}
