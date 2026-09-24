import { dehydrate, HydrationBoundary } from "@tanstack/react-query";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { getQueryClient } from "@/lib/query-client";
import { pendingInviteListQuery } from "@/features/workspaces/invites/queries";
import { getSessionApi, requireUser } from "@/features/auth/server";
import { getTimeZone } from "@/lib/time-zone/server";

import { PendingInvites } from "@/features/workspaces/invites/components/pending-invites";

export const metadata: Metadata = { title: "Your invitations" };

/** Where `/` sends a user with no workspace and invitations waiting. */
export default function InvitesPage() {
  return (
    <Suspense fallback={<Skeleton className="h-64 w-full" />}>
      <InvitesContent />
    </Suspense>
  );
}

async function InvitesContent() {
  await requireUser();
  const [api, timeZone] = await Promise.all([getSessionApi(), getTimeZone()]);
  const queryClient = getQueryClient();
  const invites = await queryClient.query(pendingInviteListQuery(api));
  if (invites.length === 0) redirect("/onboarding");

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <Card>
        <CardHeader>
          <CardTitle>You have been invited</CardTitle>
          <CardDescription>
            Accept an invitation to join that workspace. Anything you leave here stays available in
            your account settings.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <PendingInvites timeZone={timeZone} whenEmpty="onboarding" />
        </CardContent>
      </Card>
    </HydrationBoundary>
  );
}
