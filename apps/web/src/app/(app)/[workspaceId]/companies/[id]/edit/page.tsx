import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { getSessionApi } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";

import { CompanyForm } from "@/features/crm/companies/components/company-form";

export const metadata: Metadata = { title: "Edit company" };

type Params = Promise<{ workspaceId: string; id: string }>;

export default function EditCompanyPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <EditCompanyForm params={params} />
    </Suspense>
  );
}

async function EditCompanyForm({ params }: { params: Params }) {
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const api = await getSessionApi();
  const { data: company } = await api.GET("/workspaces/{workspace_id}/companies/{company_id}", {
    params: { path: { workspace_id: workspaceId, company_id: id } },
  });
  if (!company) notFound();
  return (
    <FormPage>
      <PageHeader title={company.name} />
      <CompanyForm company={company} />
    </FormPage>
  );
}
