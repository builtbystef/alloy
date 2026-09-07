import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { requireUser, requireWorkspace } from "@/lib/session";

import { PasswordForm } from "./password-form";
import { SessionsCard } from "./sessions-card";

export const metadata: Metadata = { title: "Account" };

type Params = Promise<{ workspaceId: string }>;

export default function AccountPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Account" description="Your login, across every workspace." />
      <Suspense fallback={<FormSkeleton />}>
        <AccountContent params={params} />
      </Suspense>
    </>
  );
}

async function AccountContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const [user] = await Promise.all([requireUser(), requireWorkspace(workspaceId)]);
  return (
    <div className="grid max-w-3xl gap-6 md:grid-cols-2">
      <PasswordForm email={user.email} />
      <SessionsCard />
    </div>
  );
}
