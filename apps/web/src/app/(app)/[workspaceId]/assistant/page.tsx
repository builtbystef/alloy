import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { latestConversation } from "@/features/assistant/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { workspacePaths } from "@/lib/routes";

import { ChatSkeleton } from "@/features/assistant/components/chat-skeleton";

export const metadata: Metadata = { title: "Assistant" };

type Params = Promise<{ workspaceId: string }>;

/** `/assistant` opens the most recent conversation, or starts one. */
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
  const conversation = await latestConversation(workspaceId);
  redirect(workspacePaths(workspaceId).assistantChat(conversation.id));
}
