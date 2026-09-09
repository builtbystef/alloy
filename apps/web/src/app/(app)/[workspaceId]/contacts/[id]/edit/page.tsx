import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { companyPickerQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { ContactForm } from "../../contact-form";

export const metadata: Metadata = { title: "Edit contact" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function EditContactPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Edit contact" />
      <Suspense fallback={<FormSkeleton />}>
        <EditContactForm params={params} />
      </Suspense>
    </>
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
    queryClient.prefetchQuery(companyPickerQuery(api, workspaceId, "")),
  ]);
  if (!contact) notFound();
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ContactForm contact={contact} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
