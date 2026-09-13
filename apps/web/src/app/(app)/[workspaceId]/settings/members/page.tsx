import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { SettingsSection, SettingsSections } from "@/components/shared/layout/settings-section";
import { TableSkeleton } from "@/components/shared/skeletons";
import { inviteListQuery, memberListQuery } from "@/features/workspaces/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireUser } from "@/lib/auth/session";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { Invites } from "@/features/workspaces/components/invites";
import { MembersTable } from "@/features/workspaces/components/members-table";

export const metadata: Metadata = { title: "Members" };

type Params = Promise<{ workspaceId: string }>;

export default function MembersPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<TableSkeleton rows={3} />}>
      <MembersContent params={params} />
    </Suspense>
  );
}

async function MembersContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const [workspace, user] = await Promise.all([requireWorkspace(workspaceId), requireUser()]);
  const canManage = workspace.permissions.includes("members:manage");
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.query(memberListQuery(api, workspaceId)).catch(noop),
    // The invitation list is admin-only; a viewer's request would be a 403.
    canManage ? queryClient.query(inviteListQuery(api, workspaceId)).catch(noop) : null,
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <SettingsSections>
        <SettingsSection
          wide
          title="Members"
          description="Owners can do everything; admins manage members and settings; members edit records; viewers only read."
        >
          <MembersTable timeZone={timeZone} currentEmail={user.email} />
        </SettingsSection>
        {canManage && (
          <SettingsSection
            wide
            title="Invitations"
            description="Invite someone by email. The link works for seven days, for that address only."
          >
            <Invites timeZone={timeZone} />
          </SettingsSection>
        )}
      </SettingsSections>
    </HydrationBoundary>
  );
}
