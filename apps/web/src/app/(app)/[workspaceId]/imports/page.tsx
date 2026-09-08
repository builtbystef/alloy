import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { importListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseImportSearch } from "@/lib/schemas";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";
import { Can } from "@/lib/workspace";

import { ImportCard } from "./import-card";
import { ImportsTable } from "./imports-table";

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
    <>
      <PageHeader
        title="Imports"
        description="Load contacts or companies from a CSV file. Rows that already exist are skipped."
      />
      <Suspense fallback={<TableSkeleton rows={3} />}>
        <ImportsContent params={params} searchParams={searchParams} />
      </Suspense>
    </>
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
  await queryClient.prefetchQuery(importListQuery(api, workspaceId));

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
