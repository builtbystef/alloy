import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { Button } from "@/components/ui/button";
import { companyListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseCompanySearch, toSearchString } from "@/lib/schemas";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { Can } from "@/lib/workspace";
import { getTimeZone } from "@/lib/time-zone";

import { CompaniesTable } from "./companies-table";

export const metadata: Metadata = { title: "Companies" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function CompaniesPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <>
      <PageHeader title="Companies" description="The organisations your contacts belong to.">
        <Can permission="crm:write">
          <Suspense>
            <NewCompanyButton params={params} />
          </Suspense>
        </Can>
      </PageHeader>
      <Suspense fallback={<TableSkeleton />}>
        <CompaniesContent params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function NewCompanyButton({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return (
    <Button nativeButton={false} render={<Link href={workspacePaths(workspaceId).companyNew} />}>
      <PlusIcon /> New company
    </Button>
  );
}

async function CompaniesContent({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const filters = parseCompanySearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(companyListQuery(api, workspaceId, filters));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CompaniesTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
