import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DetailSkeleton } from "@/components/shared/skeletons";
import { ApiError } from "@/lib/api/errors";
import { taskQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { TaskDetail } from "@/features/crm/tasks/components/task-detail";

export const metadata: Metadata = { title: "Task" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function TaskPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <TaskContent params={params} />
    </Suspense>
  );
}

async function TaskContent({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();

  try {
    await queryClient.query(taskQuery(api, workspaceId, id));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TaskDetail id={id} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
