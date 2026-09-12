import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { paged } from "@/lib/lists";
import { taskListQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseTaskSearch } from "@/features/crm/tasks/schemas";
import { toSearchString } from "@/lib/lists";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { TasksTable } from "@/features/crm/tasks/components/tasks-table";

export const metadata: Metadata = { title: "Tasks" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function TasksPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <>
      <PageHeader title="Tasks" description="Soonest due first; undated tasks last." />
      <Suspense fallback={<TableSkeleton />}>
        <TasksContent params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function TasksContent({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const filters = parseTaskSearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient
    .query(taskListQuery(api, workspaceId, { ...paged(filters), tz: timeZone }))
    .catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TasksTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
