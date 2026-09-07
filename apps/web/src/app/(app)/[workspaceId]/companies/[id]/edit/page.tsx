import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { getSessionApi, requireWorkspace } from "@/lib/session";

import { CompanyForm } from "../../company-form";

export const metadata: Metadata = { title: "Edit company" };

type Params = Promise<{ workspaceId: string; id: string }>;

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
  const { workspaceId, id } = await params;
  await requireWorkspace(workspaceId);
  const api = await getSessionApi();
  const { data: company } = await api.GET("/workspaces/{workspace_id}/companies/{company_id}", {
    params: { path: { workspace_id: workspaceId, company_id: id } },
  });
  if (!company) notFound();
  return <CompanyForm company={company} />;
}
