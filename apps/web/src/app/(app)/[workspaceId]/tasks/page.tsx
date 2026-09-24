import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import { paged, toSearchString } from "@/lib/lists";
import { taskListQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseTaskSearch } from "@/features/crm/tasks/schemas";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { Can } from "@/features/workspaces/workspace-provider";
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
      <PageHeader>
        <Can permission="crm:write">
          <Suspense>
            <NewTaskButton params={params} />
          </Suspense>
        </Can>
      </PageHeader>
      <Suspense fallback={<TableSkeleton />}>
        <TasksContent params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function NewTaskButton({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return (
    <Button nativeButton={false} render={<Link href={workspacePaths(workspaceId).taskNew} />}>
      <PlusIcon /> New task
    </Button>
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
