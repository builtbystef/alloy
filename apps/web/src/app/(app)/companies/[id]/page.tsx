import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DetailSkeleton } from "@/components/skeletons";
import { ApiError } from "@/lib/api-error";
import { companyContactsQuery, companyQuery, taskListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { CompanyDetail } from "./company-detail";

export const metadata: Metadata = { title: "Company" };

type Params = Promise<{ id: string }>;

export default function CompanyPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<DetailSkeleton />}>
      <CompanyContent params={params} />
    </Suspense>
  );
}

async function CompanyContent({ params }: { params: Params }) {
  await requireUser();
  const { id } = await params;
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();

  try {
    await Promise.all([
      queryClient.fetchQuery(companyQuery(api, id)),
      queryClient.prefetchQuery(companyContactsQuery(api, id)),
      queryClient.prefetchQuery(taskListQuery(api, { company_id: id, tz: timeZone })),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <CompanyDetail id={id} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
