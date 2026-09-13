import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import { FileUpIcon, PlusIcon } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { TableSkeleton } from "@/components/shared/skeletons";
import { Button } from "@/components/ui/button";
import { contactListQuery } from "@/features/crm/contacts/queries";
import { paged } from "@/lib/lists";
import { getQueryClient } from "@/lib/query-client";
import { parseContactSearch } from "@/features/crm/contacts/schemas";
import { toSearchString } from "@/lib/lists";
import { workspacePaths } from "@/lib/routes";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { Can } from "@/features/workspaces/workspace-provider";
import { getTimeZone } from "@/lib/time-zone/server";

import { ContactsTable } from "@/features/crm/contacts/components/contacts-table";

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
      <PageHeader>
        <Can permission="crm:write">
          <Suspense>
            <ImportButton params={params} />
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

async function ImportButton({ params }: { params: Params }) {
  const { workspaceId } = await params;
  return (
    <Button
      variant="outline"
      nativeButton={false}
      render={<Link href={`${workspacePaths(workspaceId).imports}?kind=contacts`} />}
    >
      <FileUpIcon /> Import CSV
    </Button>
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
  await queryClient.query(contactListQuery(api, workspaceId, paged(filters))).catch(noop);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Keyed so a real navigation (back/forward) resets the client filters, page, and sort. */}
      <ContactsTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
