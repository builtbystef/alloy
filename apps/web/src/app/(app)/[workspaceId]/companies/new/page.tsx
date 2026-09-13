import type { Metadata } from "next";
import { Suspense } from "react";

import { FormPage } from "@/components/shared/layout/form-page";
import { FormSkeleton } from "@/components/shared/skeletons";
import { requireWorkspace } from "@/features/workspaces/server";

import { CompanyForm } from "@/features/crm/companies/components/company-form";

export const metadata: Metadata = { title: "New company" };

type Params = Promise<{ workspaceId: string }>;

export default function NewCompanyPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <NewCompanyForm params={params} />
    </Suspense>
  );
}

async function NewCompanyForm({ params }: { params: Params }) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  return (
    <FormPage>
      <CompanyForm />
    </FormPage>
  );
}
