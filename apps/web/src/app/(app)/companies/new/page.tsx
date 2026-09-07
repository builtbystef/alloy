import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { requireUser } from "@/lib/session";

import { CompanyForm } from "../company-form";

export const metadata: Metadata = { title: "New company" };

export default function NewCompanyPage() {
  return (
    <>
      <PageHeader title="New company" />
      <Suspense fallback={<FormSkeleton />}>
        <NewCompanyForm />
      </Suspense>
    </>
  );
}

async function NewCompanyForm() {
  await requireUser();
  return <CompanyForm />;
}
