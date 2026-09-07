import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { taskListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseTaskSearch, toSearchString } from "@/lib/schemas";
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { TasksTable } from "./tasks-table";

export const metadata: Metadata = { title: "Tasks" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function TasksPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <>
      <PageHeader title="Tasks" description="Soonest due first; undated tasks last." />
      <Suspense fallback={<TableSkeleton />}>
        <TasksContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function TasksContent({ searchParams }: { searchParams: SearchParams }) {
  await requireUser();
  const filters = parseTaskSearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(taskListQuery(api, { ...filters, tz: timeZone }));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <TasksTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
