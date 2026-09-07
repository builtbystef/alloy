import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { requireWorkspace } from "@/lib/session";

import { CompanyForm } from "../company-form";

export const metadata: Metadata = { title: "New company" };

type Params = Promise<{ workspaceId: string }>;

export default function NewCompanyPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="New company" />
      <Suspense fallback={<FormSkeleton />}>
        <NewCompanyForm params={params} />
      </Suspense>
    </>
  );
}

async function NewCompanyForm({ params }: { params: Params }) {
  const { workspaceId } = await params;
  await requireWorkspace(workspaceId);
  return <CompanyForm />;
}
