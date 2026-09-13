import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { companyPickerQuery } from "@/features/crm/companies/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ContactForm } from "@/features/crm/contacts/components/contact-form";

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
    <Suspense fallback={<FormSkeleton />}>
      <NewContactForm params={params} searchParams={searchParams} />
    </Suspense>
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
  await queryClient.query(companyPickerQuery(api, workspaceId, "")).catch(noop);
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <FormPage>
        <ContactForm
          timeZone={timeZone}
          {...(typeof company_id === "string" ? { defaultCompanyId: company_id } : {})}
        />
      </FormPage>
    </HydrationBoundary>
  );
}
