import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { companyPickerQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { ContactForm } from "../contact-form";

export const metadata: Metadata = { title: "New contact" };

type Params = Promise<{ workspaceId: string }>;
type SearchParams = Promise<{ company_id?: string | string[] }>;

export default function NewContactPage({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  return (
    <>
      <PageHeader title="New contact" />
      <Suspense fallback={<FormSkeleton />}>
        <NewContactForm params={params} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

async function NewContactForm({
  params,
  searchParams,
}: {
  params: Params;
  searchParams: SearchParams;
}) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  const { company_id } = await searchParams;
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await queryClient.prefetchQuery(companyPickerQuery(api, workspaceId, ""));
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ContactForm
        timeZone={timeZone}
        {...(typeof company_id === "string" ? { defaultCompanyId: company_id } : {})}
      />
    </HydrationBoundary>
  );
}
