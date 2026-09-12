import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import { Suspense, type ReactNode } from "react";

import { Skeleton } from "@/components/ui/skeleton";
import { conversationListQuery } from "@/features/assistant/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ConversationList } from "@/features/assistant/components/conversation-list";

type Params = Promise<{ workspaceId: string }>;

export default function AssistantLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: Params;
}) {
  return (
    <div className="-my-2 flex h-[calc(100dvh-3.5rem-3rem)] min-h-[28rem] gap-6 md:-my-4">
      <aside className="hidden w-60 shrink-0 md:flex md:flex-col">
        <Suspense fallback={<ListSkeleton />}>
          <ConversationListContent params={params} />
        </Suspense>
      </aside>
      <section className="flex min-h-0 min-w-0 flex-1 flex-col rounded-xl bg-card ring-1 ring-foreground/10">
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
    <div className="flex flex-col gap-2">
      <Skeleton className="h-8 w-full" />
      {Array.from({ length: 5 }, (_, i) => (
        <Skeleton key={i} className="h-10 w-full" />
      ))}
    </div>
  );
}
