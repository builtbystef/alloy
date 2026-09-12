import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/shared/layout/page-header";
import { FormSkeleton } from "@/components/shared/skeletons";
import { requireUser } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";

import { DeleteAccountCard } from "@/features/auth/components/delete-account-card";
import { EmailForm } from "@/features/auth/components/email-form";
import { PasswordForm } from "@/features/auth/components/password-form";
import { SessionsCard } from "@/features/auth/components/sessions-card";

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
      <EmailForm email={user.email} pendingEmail={user.pending_email} />
      <PasswordForm email={user.email} />
      <SessionsCard />
      <DeleteAccountCard />
    </div>
  );
}
