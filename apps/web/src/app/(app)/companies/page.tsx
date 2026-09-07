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
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { CompaniesTable } from "./companies-table";

export const metadata: Metadata = { title: "Companies" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default function CompaniesPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <>
      <PageHeader title="Companies" description="The organisations your contacts belong to.">
        <Button nativeButton={false} render={<Link href="/companies/new" />}>
          <PlusIcon /> New company
        </Button>
      </PageHeader>
      <Suspense fallback={<TableSkeleton />}>
        <CompaniesContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function CompaniesContent({ searchParams }: { searchParams: SearchParams }) {
  await requireUser();
  const filters = parseCompanySearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(companyListQuery(api, filters));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CompaniesTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
