import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DetailSkeleton } from "@/components/shared/skeletons";
import { ApiError } from "@/lib/api/errors";
import { ALL_ROWS } from "@/lib/lists";
import { contactActivitiesQuery, contactQuery } from "@/features/crm/contacts/queries";
import { attachmentsQuery } from "@/features/crm/attachments/queries";
import { taskListQuery } from "@/features/crm/tasks/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ContactDetail } from "@/features/crm/contacts/components/contact-detail";

export const metadata: Metadata = { title: "Contact" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function ContactPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ContactContent params={params} />
    </Suspense>
  );
}

async function ContactContent({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();

  // The contact itself must exist for the page to make sense; the feed, tasks,
  // and attachments are prefetched alongside so the client renders without a
  // waterfall.
  try {
    await Promise.all([
      queryClient.query(contactQuery(api, workspaceId, id)),
      queryClient.query(contactActivitiesQuery(api, workspaceId, id)).catch(noop),
      queryClient.query(attachmentsQuery(api, workspaceId, { contactId: id })).catch(noop),
      queryClient
        .query(taskListQuery(api, workspaceId, { contact_id: id, ...ALL_ROWS, tz: timeZone }))
        .catch(noop),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ContactDetail id={id} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
