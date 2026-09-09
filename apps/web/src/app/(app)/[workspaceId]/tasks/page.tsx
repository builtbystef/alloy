import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { paged, taskListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseTaskSearch, toSearchString } from "@/lib/schemas";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { TasksTable } from "./tasks-table";

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
  await queryClient.prefetchQuery(
    taskListQuery(api, workspaceId, { ...paged(filters), tz: timeZone }),
  );

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TasksTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
