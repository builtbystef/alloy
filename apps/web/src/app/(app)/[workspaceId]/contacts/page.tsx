import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { Button } from "@/components/ui/button";
import { contactListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { parseContactSearch, toSearchString } from "@/lib/schemas";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { Can } from "@/lib/workspace";
import { getTimeZone } from "@/lib/time-zone";

import { ContactsTable } from "./contacts-table";

export const metadata: Metadata = { title: "Contacts" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * The static header ships in the prerendered shell. The list reads the URL
 * and the session, so it streams: the server prefetches into a fresh
 * QueryClient and hands the cache to the client table through
 * <HydrationBoundary>, where sorting, filtering, and mutations take over.
 */
export default function ContactsPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <>
      <PageHeader title="Contacts" description="Everyone you are working with.">
        <Can permission="crm:write">
          <Suspense>
            <NewContactButton params={params} />
          </Suspense>
        </Can>
      </PageHeader>
      <Suspense fallback={<TableSkeleton />}>
        <ContactsContent params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function NewContactButton({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return (
    <Button nativeButton={false} render={<Link href={workspacePaths(workspaceId).contactNew} />}>
      <PlusIcon /> New contact
    </Button>
  );
}

async function ContactsContent({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const filters = parseContactSearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(contactListQuery(api, workspaceId, filters));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Keyed so a real navigation (back/forward) resets the client filters. */}
      <ContactsTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
