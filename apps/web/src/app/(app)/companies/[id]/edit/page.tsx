import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { getSessionApi, requireUser } from "@/lib/session";

import { CompanyForm } from "../../company-form";

export const metadata: Metadata = { title: "Edit company" };

type Params = Promise<{ id: string }>;

export default function EditCompanyPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Edit company" />
      <Suspense fallback={<FormSkeleton />}>
        <EditCompanyForm params={params} />
      </Suspense>
    </>
  );
}

async function EditCompanyForm({ params }: { params: Params }) {
  await requireUser();
  const { id } = await params;
  const api = await getSessionApi();
  const { data: company } = await api.GET("/companies/{company_id}", {
    params: { path: { company_id: id } },
  });
  if (!company) notFound();
  return <CompanyForm company={company} />;
}
