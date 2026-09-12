import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { ApiError } from "@/lib/api/errors";
import { conversationQuery } from "@/features/assistant/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ChatPanel } from "@/features/assistant/components/chat-panel";
import { ChatSkeleton } from "@/features/assistant/components/chat-skeleton";
import type { ChatMessage } from "@/features/assistant/types";

export const metadata: Metadata = { title: "Assistant" };

type Params = Promise<{ workspaceId: string; conversationId: string }>;

export default function ConversationPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<ChatSkeleton />}>
      <ConversationContent params={params} />
    </Suspense>
  );
}

/**
 * The transcript is fetched here and handed to the chat as its starting
 * messages; from then on `useChat` owns it, so there is no query to hydrate.
 */
async function ConversationContent({ params }: { params: Params }) {
  const { workspaceId, conversationId } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  let detail;
  try {
    detail = await getQueryClient().query(conversationQuery(api, workspaceId, conversationId));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }
  return (
    <ChatPanel
      key={conversationId}
      conversationId={conversationId}
      initialMessages={detail.messages as unknown as ChatMessage[]}
      timeZone={timeZone}
    />
  );
}
