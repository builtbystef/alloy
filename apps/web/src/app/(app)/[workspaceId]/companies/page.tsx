import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import { FileUpIcon, PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import { companyListQuery } from "@/features/crm/companies/queries";
import { paged, toSearchString } from "@/lib/lists";
import { getQueryClient } from "@/lib/query-client";
import { parseCompanySearch } from "@/features/crm/companies/schemas";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { Can } from "@/features/workspaces/workspace-provider";
import { getTimeZone } from "@/lib/time-zone/server";

import { CompaniesTable } from "@/features/crm/companies/components/companies-table";

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
      <PageHeader>
        <Can permission="crm:write">
          <Suspense>
            <ImportButton params={params} />
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

async function ImportButton({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return (
    <Button
      variant="outline"
      nativeButton={false}
      render={<Link href={`${workspacePaths(workspaceId).imports}?kind=companies`} />}
    >
      <FileUpIcon /> Import CSV
    </Button>
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
  await queryClient.query(companyListQuery(api, workspaceId, paged(filters))).catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CompaniesTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
