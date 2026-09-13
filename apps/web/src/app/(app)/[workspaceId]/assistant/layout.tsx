import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import { Suspense, type ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { conversationListQuery } from "@/features/assistant/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ConversationList } from "@/features/assistant/components/conversation-list";
import { NewChatButton } from "@/features/assistant/components/new-chat-button";

type Params = Promise<{ workspaceId: string }>;

/**
 * Two panes filling the space under the shell header: the conversation list,
 * flush against the app sidebar, and the chat. The page positions itself
 * against the shell's main column to escape the centered content width; on
 * small screens the list gives way to a bar with New chat.
 */
export default function AssistantLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Params;
}) {
  return (
    <div className="absolute inset-x-0 top-14 bottom-0 flex">
      <aside className="hidden w-64 shrink-0 border-r bg-muted/30 md:flex md:flex-col">
        <Suspense fallback={<ListSkeleton />}>
          <ConversationListContent params={params} />
        </Suspense>
      </aside>
      <section className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex shrink-0 items-center justify-end border-b px-3 py-2 md:hidden">
          <Suspense>
            <NewChatButton variant="ghost" size="sm" />
          </Suspense>
        </div>
        {children}
      </section>
    </div>
  );
}

async function ConversationListContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.query(conversationListQuery(api, workspaceId)).catch(noop);
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ConversationList timeZone={timeZone} />
    </HydrationBoundary>
  );
}

function ListSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-3">
      <Skeleton className="h-8 w-full" />
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-11 w-full" />
      ))}
    </div>
  );
}
