import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { FormSkeleton } from "@/components/skeletons";
import { requireUser } from "@/lib/session";

import { PasswordForm } from "./password-form";
import { SessionsCard } from "./sessions-card";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return (
    <>
      <PageHeader title="Settings" />
      <Suspense fallback={<FormSkeleton />}>
        <SettingsContent />
      </Suspense>
    </>
  );
}

async function SettingsContent() {
  const user = await requireUser();
  return (
    <div className="grid max-w-3xl gap-6 md:grid-cols-2">
      <PasswordForm email={user.email} />
      <SessionsCard />
    </div>
  );
}
