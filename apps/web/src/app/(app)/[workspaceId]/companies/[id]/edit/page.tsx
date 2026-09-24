import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { getSessionApi } from "@/features/auth/server";
import { companyQuery } from "@/features/crm/companies/queries";
import { ApiError } from "@/lib/api/errors";
import { getQueryClient } from "@/lib/query-client";
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
  let company;
  try {
    company = await getQueryClient().query(companyQuery(api, workspaceId, id));
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 422)) notFound();
    throw error;
  }
  return (
    <FormPage>
      <PageHeader title={company.name} />
      <CompanyForm company={company} />
    </FormPage>
  );
}
