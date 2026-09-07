import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { Suspense } from "react";

import { PageHeader } from "@/components/page-header";
import { TableSkeleton } from "@/components/skeletons";
import { inviteListQuery, memberListQuery } from "@/lib/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi, requireUser, requireWorkspace } from "@/lib/session";
import { getTimeZone } from "@/lib/time-zone";

import { InvitesCard } from "./invites-card";
import { MembersTable } from "./members-table";

export const metadata: Metadata = { title: "Members" };

type Params = Promise<{ workspaceId: string }>;

export default function MembersPage({ params }: { params: Params }) {
  return (
    <>
      <PageHeader title="Members" description="Who can see this workspace, and what they may do." />
      <Suspense fallback={<TableSkeleton rows={3} />}>
        <MembersContent params={params} />
      </Suspense>
    </>
  );
}

async function MembersContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const [workspace, user] = await Promise.all([requireWorkspace(workspaceId), requireUser()]);
  const canManage = workspace.permissions.includes("members:manage");
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  await Promise.all([
    queryClient.prefetchQuery(memberListQuery(api, workspaceId)),
    // The invitation list is admin-only; a viewer's request would be a 403.
    canManage ? queryClient.prefetchQuery(inviteListQuery(api, workspaceId)) : null,
  ]);

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <div className="flex flex-col gap-6">
        <MembersTable timeZone={timeZone} currentEmail={user.email} />
        {canManage && <InvitesCard timeZone={timeZone} />}
      </div>
    </HydrationBoundary>
  );
}
