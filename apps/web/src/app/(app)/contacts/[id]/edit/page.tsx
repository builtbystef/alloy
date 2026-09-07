import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { companyListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireUser } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { ContactForm } from "../../contact-form";

export const metadata: Metadata = { title: "Edit contact" };

type Params = Promise<{ id: string }>;

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
  await requireUser();
  const { id } = await params;
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  const [{ data: contact }] = await Promise.all([
    api.GET("/contacts/{contact_id}", { params: { path: { contact_id: id } } }),
    queryClient.prefetchQuery(companyListQuery(api, {})),
  ]);
  if (!contact) notFound();
  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ContactForm contact={contact} timeZone={timeZone} />
    </HydrationBoundary>
  );
}
