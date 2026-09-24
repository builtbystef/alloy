import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { TableSkeleton } from "@/components/shared/skeletons";
import { importListQuery } from "@/features/crm/imports/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseImportSearch } from "@/features/crm/imports/schemas";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";
import { Can } from "@/features/workspaces/workspace-provider";

import { ImportCard } from "@/features/crm/imports/components/import-card";
import { ImportsTable } from "@/features/crm/imports/components/imports-table";

export const metadata: Metadata = { title: "Imports" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * Upload a CSV, then watch it load. The card only shows to roles that may
 * write; the history below it is for everyone. `?kind=companies` preselects
 * the kind, for the links from the contacts and companies pages.
 */
export default function ImportsPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <Suspense fallback={<TableSkeleton rows={3} />}>
      <ImportsContent params={params} searchParams={searchParams} />
    </Suspense>
  );
}

async function ImportsContent({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const { kind } = parseImportSearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.query(importListQuery(api, workspaceId)).catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <div className="flex flex-col gap-6">
        <Can permission="crm:write">
          <ImportCard initialKind={kind} />
        </Can>
        <ImportsTable timeZone={timeZone} />
      </div>
    </HydrationBoundary>
  );
}
