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
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { ContactsTable } from "./contacts-table";

export const metadata: Metadata = { title: "Contacts" };

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

/**
 * The static header ships in the prerendered shell. The list reads the URL
 * and the session, so it streams: the server prefetches into a fresh
 * QueryClient and hands the cache to the client table through
 * <HydrationBoundary>, where sorting, filtering, and mutations take over.
 */
export default function ContactsPage({ searchParams }: { searchParams: SearchParams }) {
  return (
    <>
      <PageHeader title="Contacts" description="Everyone you are working with.">
        <Button nativeButton={false} render={<Link href="/contacts/new" />}>
          <PlusIcon /> New contact
        </Button>
      </PageHeader>
      <Suspense fallback={<TableSkeleton />}>
        <ContactsContent searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function ContactsContent({ searchParams }: { searchParams: SearchParams }) {
  await requireUser();
  const filters = parseContactSearch(await searchParams);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(contactListQuery(api, filters));

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      {/* Keyed so a real navigation (back/forward) resets the client filters. */}
      <ContactsTable key={toSearchString(filters)} initialFilters={filters} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
