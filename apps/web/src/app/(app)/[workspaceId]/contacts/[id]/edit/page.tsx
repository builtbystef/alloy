import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { companyPickerQuery } from "@/features/crm/companies/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { ContactForm } from "@/features/crm/contacts/components/contact-form";

export const metadata: Metadata = { title: "Edit contact" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function EditContactPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <EditContactForm params={params} />
    </Suspense>
  );
}

async function EditContactForm({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  const [{ data: contact }] = await Promise.all([
    api.GET("/workspaces/{workspace_id}/contacts/{contact_id}", {
      params: { path: { workspace_id: workspaceId, contact_id: id } },
    }),
    queryClient.query(companyPickerQuery(api, workspaceId, "")).catch(noop),
  ]);
  if (!contact) notFound();
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <FormPage>
        <PageHeader title={contact.name} />
        <ContactForm contact={contact} timeZone={timeZone} />
      </FormPage>
    </HydrationBoundary>
  );
}
