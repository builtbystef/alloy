import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { SettingsSection, SettingsSections } from "@/components/shared/layout/settings-section";
import { FormSkeleton } from "@/components/shared/skeletons";
import { getQueryClient } from "@/lib/query-client";
import { pendingInviteListQuery } from "@/features/workspaces/invites/queries";
import { getSessionApi, requireUser } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { DeleteAccountCard } from "@/features/auth/components/delete-account-card";
import { EmailForm } from "@/features/auth/components/email-form";
import { NameForm } from "@/features/auth/components/name-form";
import { PasswordForm } from "@/features/auth/components/password-form";
import { SessionsCard } from "@/features/auth/components/sessions-card";
import { PendingInvites } from "@/features/workspaces/invites/components/pending-invites";

export const metadata: Metadata = { title: "Settings" };

type Params = Promise<{ workspaceId: string }>;

export default function AccountPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<FormSkeleton />}>
      <AccountContent params={params} />
    </Suspense>
  );
}

async function AccountContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const [user, , api, timeZone] = await Promise.all([
    requireUser(),
    requireWorkspace(workspaceId),
    getSessionApi(),
    getTimeZone(),
  ]);
  const queryClient = getQueryClient();
  const invites = await queryClient.query(pendingInviteListQuery(api));
  return (
    <SettingsSections>
      {invites.length > 0 && (
        <SettingsSection
          wide
          title="Invitations"
          description="Workspaces you have been invited to join."
        >
          <HydrationBoundary state={dehydrate(queryClient)}>
            <PendingInvites timeZone={timeZone} />
          </HydrationBoundary>
        </SettingsSection>
      )}
      <SettingsSection title="Profile" description="How you appear across your workspaces.">
        <NameForm name={user.name} />
      </SettingsSection>
      <SettingsSection
        title="Email"
        description={
          <>
            You log in as <strong className="font-medium text-foreground">{user.email}</strong>. A
            new address takes effect once you follow the link we send to it.
          </>
        }
      >
        <EmailForm pendingEmail={user.pending_email} />
      </SettingsSection>
      <SettingsSection title="Password" description="Changing it logs out every other device.">
        <PasswordForm email={user.email} />
      </SettingsSection>
      <SettingsSection
        title="Sessions"
        description="Sessions last 30 days. If a device is lost, log out everywhere."
      >
        <SessionsCard />
      </SettingsSection>
      <SettingsSection
        title="Delete account"
        description="Logs you out everywhere and removes the account after 7 days, along with every workspace you are the only member of. Logging in before then cancels it."
      >
        <DeleteAccountCard />
      </SettingsSection>
    </SettingsSections>
  );
}
