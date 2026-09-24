import { dehydrate, HydrationBoundary, noop } from "@tanstack/react-query";
import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { importListQuery } from "@/features/crm/imports/queries";
import { getQueryClient } from "@/lib/query-client";
import { getSessionApi } from "@/features/auth/server";
import { requireWorkspace } from "@/features/workspaces/server";
import { getTimeZone } from "@/lib/time-zone/server";
import { WorkspaceProvider } from "@/features/workspaces/workspace-provider";

import { ImportStep } from "@/features/workspaces/components/import-step";
import { OnboardingSteps } from "@/features/workspaces/components/onboarding-steps";

export const metadata: Metadata = { title: "Set up your workspace" };

type Params = Promise<{ workspaceId: string }>;

/**
 * Step two: import a CSV, or skip. Both finish onboarding and open the
 * workspace. Only for those who can finish it, while it is unfinished.
 */
export default function WorkspaceOnboardingPage({ params }: { params: Params }) {
  return (
    <Suspense fallback={<Skeleton className="h-96 w-full" />}>
      <OnboardingContent params={params} />
    </Suspense>
  );
}

async function OnboardingContent({ params }: { params: Params }) {
  const { workspaceId } = await params;
  const [workspace, api, timeZone] = await Promise.all([
    requireWorkspace(workspaceId),
    getSessionApi(),
    getTimeZone(),
  ]);
  if (workspace.onboarded_at !== null || !workspace.permissions.includes("workspace:manage")) {
    redirect(`/${workspace.id}`);
  }
  const queryClient = getQueryClient();
  await queryClient.query(importListQuery(api, workspaceId)).catch(noop);

  return (
    <WorkspaceProvider workspace={Promise.resolve(workspace)}>
      <HydrationBoundary state={dehydrate(queryClient)}>
        <Card>
          <CardHeader>
            <OnboardingSteps current={2} />
            <CardTitle>Bring your data into {workspace.name}</CardTitle>
            <CardDescription>
              Import contacts or companies from a CSV export of your old tool or spreadsheet. You
              can always do this later from the Imports page.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ImportStep timeZone={timeZone} />
          </CardContent>
        </Card>
      </HydrationBoundary>
    </WorkspaceProvider>
  );
}
