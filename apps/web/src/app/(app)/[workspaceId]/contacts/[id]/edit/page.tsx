import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { companyPickerQuery } from "@/features/crm/companies/queries";
import { contactQuery } from "@/features/crm/contacts/queries";
import { ApiError } from "@/lib/api/errors";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/features/auth/server";
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
  let contact;
  try {
    [contact] = await Promise.all([
      queryClient.query(contactQuery(api, workspaceId, id)),
      queryClient.query(companyPickerQuery(api, workspaceId, "")).catch(noop),
    ]);
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <FormPage>
        <PageHeader title={contact.name} />
        <ContactForm contact={contact} timeZone={timeZone} />
      </FormPage>
    </HydrationBoundary>
  );
}
