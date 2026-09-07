import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DetailSkeleton } from "@/components/skeletons";
import { ApiError } from "@/lib/api-error";
import { contactActivitiesQuery, contactQuery, taskListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { ContactDetail } from "./contact-detail";

export const metadata: Metadata = { title: "Contact" };

type Params = Promise<{ id: string }>;

export default function ContactPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <ContactContent params={params} />
    </Suspense>
  );
}

async function ContactContent({ params }: { params: Params }) {
  await requireUser();
  const { id } = await params;
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();

  // The contact itself must exist for the page to make sense; the feed and
  // tasks are prefetched alongside so the client renders without a waterfall.
  try {
    await Promise.all([
      queryClient.fetchQuery(contactQuery(api, id)),
      queryClient.prefetchQuery(contactActivitiesQuery(api, id)),
      queryClient.prefetchQuery(taskListQuery(api, { contact_id: id, tz: timeZone })),
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
